import httpx                                                        # httpx is a popular HTTP client for Python
import os
import logging
from typing import Dict, Any, AsyncGenerator                         # AsyncGenerator is a type hint for asynchronous generators
from fastapi import HTTPException, status
from fastapi.responses import StreamingResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self):
        self.huggingface_api_key = os.getenv("HUGGINGFACE_API_KEY")
        self.api_url = "https://api-inference.huggingface.co/models"
        self.model_name = "gpt2"  # You can change this to any model you prefer
        
        if not self.huggingface_api_key:
            logger.warning("HUGGINGFACE_API_KEY not set")
            
    async def predict(self, input_text: str) -> Dict[str, Any]:
        """
        Perform prediction using the Hugging Face Inference API
        """
        if not self.huggingface_api_key:
            logger.error("HUGGINGFACE_API_KEY not set")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="HUGGINGFACE_API_KEY not set",
            )
            
        try:
            headers = {"Authorization": f"Bearer {self.huggingface_api_key}"}
            logger.info(f"Making prediction request to {self.api_url}/{self.model_name}")
            
            async with httpx.AsyncClient(verify=True) as client:                               # Create an instance of the httpx.AsyncClient class
                try:
                    response = await client.post(                                              # Make a POST request to the Hugging Face API
                        f"{self.api_url}/{self.model_name}",
                        headers=headers,
                        json={"inputs": input_text},
                        timeout=30.0,
                    )
                    
                    logger.info(f"Received response with status code: {response.status_code}")
                    
                    if response.status_code == 200:
                        result = response.json()
                        logger.info("Successfully processed prediction")
                        return result
                    else:
                        error_msg = f"Prediction failed with status {response.status_code}: {response.text}"
                        logger.error(error_msg)
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=error_msg,
                        )
                except httpx.ConnectError as e:                                                  # Handle connection errors
                    error_msg = f"Failed to connect to Hugging Face API: {str(e)}"
                    logger.error(error_msg)
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=error_msg,
                    )
                except httpx.TimeoutException:                                                     # Handle timeout errors
                    error_msg = "Request to Hugging Face API timed out"
                    logger.error(error_msg)
                    raise HTTPException(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        detail=error_msg,
                    )
                except httpx.RequestError as e:                                                    # Handle other request errors
                    error_msg = f"Request to Hugging Face API failed: {str(e)}"
                    logger.error(error_msg)
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=error_msg,
                    )
        except HTTPException:
            raise
        except Exception as e:
            error_msg = f"Unexpected error during prediction: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg,
            )
            
    async def generate(self, input_text: str) -> AsyncGenerator[Dict[str, Any], None]:                     # Define an asynchronous generator function
        """Generate streaming response using the Hugging Face Inference API"""
        if not self.huggingface_api_key:
            logger.error("HUGGINGFACE_API_KEY not set")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="HUGGINGFACE_API_KEY not set",
            )
            
        try:
            headers = {"Authorization": f"Bearer {self.huggingface_api_key}"}
            logger.info(f"Making streaming request to {self.api_url}/{self.model_name}")
            
            async with httpx.AsyncClient(verify=True) as client:
                try:
                    response = await client.post(
                        f"{self.api_url}/{self.model_name}",
                        headers=headers,
                        json={"inputs": input_text},
                        timeout=30.0,
                    )
                    
                    logger.info(f"Received response with status code: {response.status_code}")
                    
                    if response.status_code == 200:
                        result = response.json()
                        logger.info("Successfully processed streaming request")
                        yield result
                    else:
                        error_msg = f"Generation failed with status {response.status_code}: {response.text}"
                        logger.error(error_msg)
                        raise HTTPException(
                            status_code=response.status_code,
                            detail=error_msg,
                        )
                except httpx.ConnectError as e:
                    error_msg = f"Failed to connect to Hugging Face API: {str(e)}"
                    logger.error(error_msg)
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=error_msg,
                    )
                except httpx.TimeoutException:
                    error_msg = "Request to Hugging Face API timed out"
                    logger.error(error_msg)
                    raise HTTPException(
                        status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                        detail=error_msg,
                    )
                except httpx.RequestError as e:
                    error_msg = f"Request to Hugging Face API failed: {str(e)}"
                    logger.error(error_msg)
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail=error_msg,
                    )
        except HTTPException:
            raise
        except Exception as e:
            error_msg = f"Unexpected error during generation: {str(e)}"
            logger.error(error_msg)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_msg,
            )
            
    def generate_stream(self, input_text: str, prediction_data: Dict[str, Any]):
        """
        Generate streaming response using the Hugging Face Inference API
        """
        async def generate() -> AsyncGenerator[str, None]:
            try:
                headers = {"Authorization": f"Bearer {self.huggingface_api_key}"}
                async with httpx.AsyncClient() as client:
                    async with client.stream(
                        "POST",
                        f"{self.api_url}/{self.model_name}",
                        headers=headers,
                        json={
                            "inputs": input_text,
                            "parameters": {"stream": True},
                            "context": prediction_data,
                        },
                    ) as response:
                        if response.status_code != 200:
                            raise HTTPException(
                                status_code=response.status_code,
                                detail="Generation failed",
                            )
                            
                        async for chunk in response.aiter_bytes():
                            yield chunk.decode()
                            
            except Exception as e:
                logger.error(f"Generation error: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=str(e),
                )
                
        return StreamingResponse(generate(), media_type="text/event-stream")
