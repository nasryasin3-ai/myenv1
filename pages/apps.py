from django.apps import AppConfig


class PagesConfig(AppConfig):
    name = 'pages'

    def ready(self):
        from django.db.models.signals import post_migrate
        post_migrate.connect(_ensure_dev_account, sender=self)


def _ensure_dev_account(sender, **kwargs):
    """Create/update the developer account after every migration run."""
    try:
        from django.contrib.auth.models import User
        from django.contrib.auth.hashers import make_password
        from products.models import Profile

        dev_user, created = User.objects.get_or_create(
            username='flownest_dev',
            defaults={
                'email': 'dev@flownest.com',
                'is_staff': True,
                'is_superuser': True,
                'password': make_password('FlowNest@2026'),
            }
        )
        if not created:
            dev_user.is_staff = True
            dev_user.is_superuser = True
            dev_user.password = make_password('FlowNest@2026')
            dev_user.save()

        profile, _ = Profile.objects.get_or_create(user=dev_user)
        profile.role = 'developer'
        profile.is_approved = True
        profile.is_platform_admin = True
        profile.company_name = 'FlowNest Core'
        profile.save()

    except Exception:
        pass  # Silently skip if DB not ready yet
