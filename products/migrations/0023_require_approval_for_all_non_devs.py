from django.db import migrations

def require_approval_for_non_developers(apps, schema_editor):
    """
    Reset is_approved=False for all non-developer profiles so that all owners and employees
    require explicit developer/owner approval. Remove is_superuser from non-dev accounts.
    """
    try:
        Profile = apps.get_model('products', 'Profile')
        User = apps.get_model('auth', 'User')

        for profile in Profile.objects.exclude(role='developer'):
            profile.is_approved = False
            profile.save()
            
            try:
                user = User.objects.get(id=profile.user_id)
                if user.is_superuser:
                    user.is_superuser = False
                    user.is_staff = False
                    user.save()
            except Exception:
                pass
    except Exception as e:
        print(f"Warning in migration 0023: {e}")

class Migration(migrations.Migration):

    dependencies = [
        ('products', '0022_create_developer_account'),
    ]

    operations = [
        migrations.RunPython(require_approval_for_non_developers, migrations.RunPython.noop),
    ]
