from __future__ import annotations

import json
import logging
import os
import time
import urllib.request
from functools import lru_cache
from typing import Any, cast

import boto3
from fastapi import Depends, HTTPException, Request, status
from azure.cosmos import CosmosClient

from .repositories.conversation_repository import ConversationRepository
from .services.llm import LlmClient
from .services.rag import RagService
from .services.storage import StorageService
from .services.vector_store import VectorStoreClient
from .settings import Settings

logger = logging.getLogger(__name__)


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_storage() -> StorageService:
    settings = get_settings()
    conn_str = settings.azure_storage_connection_string
    if not conn_str:
        conn_str = "UseDevelopmentStorage=true"
    return StorageService(
        connection_string=conn_str,
        container_name=settings.azure_storage_container_name,
    )


@lru_cache
def get_cosmos_client() -> CosmosClient:
    settings = get_settings()
    endpoint = settings.cosmos_endpoint or "https://localhost:8081"
    key = settings.cosmos_key or "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw=="
    
    verify = True
    if "localhost" in endpoint or "127.0.0.1" in endpoint:
        verify = False
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        os.environ["AZURE_COSMOS_DISABLE_SSL_VERIFICATION"] = "true"
        
    return CosmosClient(endpoint, credential=key, connection_verify=verify)


@lru_cache
def get_conversations_container():
    client = get_cosmos_client()
    settings = get_settings()
    db = client.get_database_client(settings.cosmos_database_name)
    return db.get_container_client(settings.cosmos_conversations_container)


@lru_cache
def get_vectors_container():
    client = get_cosmos_client()
    settings = get_settings()
    db = client.get_database_client(settings.cosmos_database_name)
    return db.get_container_client(settings.cosmos_vectors_container)


def get_repository() -> ConversationRepository:
    container = get_conversations_container()
    return ConversationRepository(container)


@lru_cache
def get_vector_store() -> VectorStoreClient:
    settings = get_settings()
    container = get_vectors_container()
    api_key = settings.litellm_embedding_api_key or settings.litellm_vision_api_key
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
    return VectorStoreClient(
        container=container,
        embedding_model=settings.litellm_embedding_model,
        dimension=settings.embedding_dimension,
        gemini_api_key=api_key,
    )


@lru_cache
def get_ssm_parameter(param_name: str) -> str | None:
    try:
        ssm = boto3.client("ssm", region_name=get_settings().aws_region)
        response = ssm.get_parameter(Name=param_name, WithDecryption=True)
        return response["Parameter"]["Value"]
    except Exception:
        return None


def get_llm_client() -> LlmClient:
    settings = get_settings()
    api_key = settings.litellm_api_key

    ssm_param_name = os.getenv("LITELLM_API_KEY_PARAMETER")
    if ssm_param_name:
        ssm_key = get_ssm_parameter(ssm_param_name)
        if ssm_key:
            api_key = ssm_key

    return LlmClient(
        model=settings.litellm_model,
        api_key=api_key,
        base_url=settings.litellm_base_url,
    )


def get_vision_llm_client() -> LlmClient:
    settings = get_settings()
    api_key = settings.litellm_vision_api_key

    ssm_param_name = os.getenv("LITELLM_VISION_API_KEY_PARAMETER")
    if ssm_param_name:
        ssm_key = get_ssm_parameter(ssm_param_name)
        if ssm_key:
            api_key = ssm_key

    # Fallback to standard key if no vision API key is configured
    if not api_key:
        api_key = settings.litellm_api_key
        ssm_param_name_std = os.getenv("LITELLM_API_KEY_PARAMETER")
        if ssm_param_name_std:
            ssm_key_std = get_ssm_parameter(ssm_param_name_std)
            if ssm_key_std:
                api_key = ssm_key_std

    return LlmClient(
        model=settings.litellm_vision_model,
        api_key=api_key,
        base_url=settings.litellm_vision_base_url,
    )


@lru_cache
def get_textract_client():
    settings = get_settings()
    return boto3.client(
        "textract",
        region_name=settings.aws_region,
    )


def get_rag_service(
    vector_store: VectorStoreClient = Depends(get_vector_store),
) -> RagService:
    if hasattr(vector_store, "dependency") or type(vector_store).__name__ == "Depends":
        vector_store = get_vector_store()
    settings = get_settings()
    storage = get_storage()
    textract_client = get_textract_client()
    
    # We still instantiate boto3 S3 client to keep compatibility with textract if needed
    s3_client = None
    try:
        s3_client = boto3.client("s3", region_name=settings.aws_region)
    except Exception:
        pass
        
    return RagService(
        vector_store=vector_store,
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
        storage=storage,
        textract_client=textract_client,
        s3_client=s3_client,
        s3_bucket_name=settings.s3_bucket_name,
    )


# Cache dictionary mapping JWKS URL to (keys_dict, expiry_timestamp)
_jwks_cache: dict[str, tuple[dict, float]] = {}


def get_jwks(jwks_url: str) -> dict:
    now = time.time()
    if jwks_url in _jwks_cache:
        cached_val, expiry = _jwks_cache[jwks_url]
        if now < expiry:
            return cached_val
    try:
        with urllib.request.urlopen(jwks_url, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
            _jwks_cache[jwks_url] = (data, now + 3600)
            return data
    except Exception as e:
        logger.warning("Failed to fetch JWKS from %s: %s", jwks_url, e)
        if jwks_url in _jwks_cache:
            return _jwks_cache[jwks_url][0]
        return {"keys": []}


def get_current_user_id(
    request: Request, settings: Settings = Depends(get_settings)
) -> str:
    # 1. AWS Lambda Environment: Extract Cognito claims from API Gateway (if present)
    aws_event = request.scope.get("aws.event")
    if aws_event and isinstance(aws_event, dict):
        request_context = aws_event.get("requestContext", {})
        authorizer = request_context.get("authorizer", {})
        jwt_data = authorizer.get("jwt", {})
        claims = jwt_data.get("claims", {})
        cognito_user = claims.get("username") or claims.get("sub")
        if cognito_user:
            return cognito_user

    # 2. Extract and Validate Bearer Token from Authorization Header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]

        if token and (len(token) < 50 or token.count(".") != 2):
            if settings.cognito_user_pool_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token format",
                )
            return token

        try:
            import jwt

            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")

            if settings.cognito_user_pool_id:
                jwks_url = f"https://cognito-idp.{settings.aws_region}.amazonaws.com/{settings.cognito_user_pool_id}/.well-known/jwks.json"
                jwks = get_jwks(jwks_url)

                public_key: Any = None
                for key in jwks.get("keys", []):
                    if key.get("kid") == kid:
                        from jwt.algorithms import RSAAlgorithm

                        public_key = RSAAlgorithm.from_jwk(key)
                        break

                if public_key:
                    payload = jwt.decode(
                        token,
                        cast(Any, public_key),
                        algorithms=["RS256"],
                        audience=settings.cognito_client_id,
                        options={"verify_exp": True},
                    )
                    return _first_string_claim(
                        payload, ("sub", "email", "cognito:username")
                    )

                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token key ID not found in Cognito JWKS",
                )

            logger.warning(
                "JWKS validation skipped or key not found. Performing unverified decode for fallback."
            )
            payload = jwt.decode(token, options={"verify_signature": False})
            return _first_string_claim(
                payload, ("sub", "email", "cognito:username"), default="admin"
            )

        except Exception as e:
            logger.warning("JWT validation failed: %s", e)
            if settings.cognito_user_pool_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Signature verification failed: {str(e)}",
                )
            try:
                import jwt

                payload = jwt.decode(token, options={"verify_signature": False})
                return _first_string_claim(payload, ("sub", "email"), default="admin")
            except Exception:
                return "admin"

    # 3. Custom Local Headers
    x_user = request.headers.get("X-User-ID")
    if x_user:
        return x_user

    if settings.cognito_user_pool_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required",
        )

    return "admin"


def _first_string_claim(
    payload: dict[str, Any], keys: tuple[str, ...], default: str | None = None
) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    if default is not None:
        return default
    return cast(str, "")
