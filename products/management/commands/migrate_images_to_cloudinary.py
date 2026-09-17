from pathlib import Path

import cloudinary.uploader

from django.conf import settings
from django.core.management.base import BaseCommand

from products.models import ProductImage
from accounts.models import UserProfile


class Command(BaseCommand):
    help = "Upload existing local images to Cloudinary and update database references."

    def handle(self, *args, **options):
        media_root = Path(settings.BASE_DIR) / "media"

        if not media_root.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Media directory does not exist: {media_root}"
                )
            )
            return

        migrated = 0
        skipped = 0
        failed = 0

        # ============================================================
        # PRODUCT IMAGES
        # ============================================================

        self.stdout.write("\nMigrating product images...")

        product_images = ProductImage.objects.exclude(
            image__isnull=True
        ).exclude(
            image=""
        )

        for product_image in product_images:
            current_name = product_image.image.name

            # Skip if it already looks like a Cloudinary public ID
            # rather than a local file path.
            if not current_name:
                skipped += 1
                continue

            local_path = media_root / current_name

            if not local_path.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"SKIPPED: Local file not found: {local_path}"
                    )
                )
                skipped += 1
                continue

            try:
                self.stdout.write(
                    f"Uploading product image: {current_name}"
                )

                result = cloudinary.uploader.upload(
                    str(local_path),
                    resource_type="image",
                    use_filename=True,
                    unique_filename=True,
                    overwrite=False,
                    folder="products",
                )

                public_id = result["public_id"]

                product_image.image.name = public_id
                product_image.save(update_fields=["image"])

                migrated += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ Uploaded: {public_id}"
                    )
                )

            except Exception as exc:
                failed += 1

                self.stdout.write(
                    self.style.ERROR(
                        f"  ✗ Failed: {current_name} — {exc}"
                    )
                )

        # ============================================================
        # PROFILE PICTURES
        # ============================================================

        self.stdout.write("\nMigrating profile pictures...")

        profiles = UserProfile.objects.exclude(
            profile_picture__isnull=True
        ).exclude(
            profile_picture=""
        )

        for profile in profiles:
            current_name = profile.profile_picture.name

            if not current_name:
                skipped += 1
                continue

            local_path = media_root / current_name

            if not local_path.exists():
                self.stdout.write(
                    self.style.WARNING(
                        f"SKIPPED: Local file not found: {local_path}"
                    )
                )
                skipped += 1
                continue

            try:
                self.stdout.write(
                    f"Uploading profile picture: {current_name}"
                )

                result = cloudinary.uploader.upload(
                    str(local_path),
                    resource_type="image",
                    use_filename=True,
                    unique_filename=True,
                    overwrite=False,
                    folder="profile_picture",
                )

                public_id = result["public_id"]

                profile.profile_picture.name = public_id
                profile.save(update_fields=["profile_picture"])

                migrated += 1

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ Uploaded: {public_id}"
                    )
                )

            except Exception as exc:
                failed += 1

                self.stdout.write(
                    self.style.ERROR(
                        f"  ✗ Failed: {current_name} — {exc}"
                    )
                )

        # ============================================================
        # SUMMARY
        # ============================================================

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("Cloudinary migration complete")
        self.stdout.write("=" * 60)

        self.stdout.write(
            self.style.SUCCESS(
                f"Migrated: {migrated}"
            )
        )

        self.stdout.write(
            self.style.WARNING(
                f"Skipped:  {skipped}"
            )
        )

        if failed:
            self.stdout.write(
                self.style.ERROR(
                    f"Failed:   {failed}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Failed:   {failed}"
                )
            )