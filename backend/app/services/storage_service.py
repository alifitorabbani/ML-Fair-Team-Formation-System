import os
import json
import uuid
import httpx
from typing import Optional
from app.config.settings import settings


class StorageService:
    def __init__(self):
        self.blob_token = settings.blob_read_write_token
        self.local_dir = settings.upload_dir

    def _is_blob_configured(self) -> bool:
        return bool(self.blob_token)

    async def upload_payment_proof(self, player_id: str, filename: str, content: bytes) -> dict:
        if self._is_blob_configured():
            try:
                return await self._upload_to_blob(player_id, filename, content)
            except Exception as e:
                print(f"Blob upload failed, falling back to local storage: {e}")

        os.makedirs(self.local_dir, exist_ok=True)
        file_path = os.path.join(self.local_dir, f"{player_id}_{uuid.uuid4()}_{filename}")
        with open(file_path, "wb") as f:
            f.write(content)
        return {
            "storage_type": "local",
            "path": file_path,
            "url": None,
        }

    async def _upload_to_blob(self, player_id: str, filename: str, content: bytes) -> dict:
        safe_filename = f"{player_id}_{uuid.uuid4()}_{filename}"
        url = f"https://blob.vercel-storage.com/{safe_filename}"
        headers = {
            "Authorization": f"Bearer {self.blob_token}",
            "Content-Type": "application/octet-stream",
            "x-vercel-blob-pathname": safe_filename,
        }
        async with httpx.AsyncClient() as client:
            response = await client.put(url, content=content, headers=headers, timeout=30.0)
            response.raise_for_status()
            result = response.json()
            blob_url = result.get("url", url)
        return {
            "storage_type": "blob",
            "path": safe_filename,
            "url": blob_url,
        }

    def delete_payment_proof(self, path: Optional[str]) -> None:
        if not path:
            return
        if self._is_blob_configured():
            self._delete_from_blob(path)
        else:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass

    def _delete_from_blob(self, path: str) -> None:
        url = f"https://blob.vercel-storage.com/{path}"
        headers = {"Authorization": f"Bearer {self.blob_token}"}
        try:
            import requests
            requests.delete(url, headers=headers, timeout=10.0)
        except Exception:
            pass


storage_service = StorageService()