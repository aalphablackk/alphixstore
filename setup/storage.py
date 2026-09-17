import os

import cloudinary
import cloudinary.api
import cloudinary.uploader

from django.core.files.storage import Storage


class CloudinaryMediaStorage(Storage):
    """
    Custom Django storage backend for Cloudinary media files.

    Keeps the existing Django ImageField workflow while storing
    uploaded images in Cloudinary instead of the Vercel filesystem.
    """

    def _save(self, name, content):

        name = name.replace("\\", "/")

        folder = os.path.dirname(name)
        filename = os.path.basename(name)

        upload_options = {
            "resource_type": "image",
            "use_filename": True,
            "unique_filename": True,
            "overwrite": False,
        }

        if folder:
            upload_options["folder"] = folder

        result = cloudinary.uploader.upload(
            content,
            **upload_options,
        )

        return result["public_id"]

    def save(self, name, content, max_length=None):
        return self._save(name, content)

    def url(self, name):

        if not name:
            return ""

        return cloudinary.CloudinaryImage(
            name
        ).build_url(
            secure=True,
        )

    def delete(self, name):

        if not name:
            return

        cloudinary.uploader.destroy(
            name,
            resource_type="image",
            invalidate=True,
        )

    def exists(self, name):
        return False

    def get_available_name(self, name, max_length=None):
        return name

    def size(self, name):

        try:
            result = cloudinary.api.resource(
                name,
                resource_type="image",
            )

            return result.get("bytes", 0)

        except Exception:
            return 0