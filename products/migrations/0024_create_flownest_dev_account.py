from django.db import migrations


def create_flownest_dev(apps, schema_editor):
    """
    Create the main developer account (flownest_dev) if it doesn't exist,
    and ensure it has is_approved=True and role='developer'.
    """
    try:
        User = apps.get_model('auth', 'User')
        Profile = apps.get_model('products', 'Profile')

        # Create or get the developer user
        user, created = User.objects.get_or_create(username='flownest_dev')
        user.is_superuser = True
        user.is_staff = True
        # Set password using make_password since we can't call set_password in migrations
        from django.contrib.auth.hashers import make_password
        user.password = make_password('FlowNest@2026')
        user.save()

        # Create or get the profile
        profile, _ = Profile.objects.get_or_create(user_id=user.id)
        profile.role = 'developer'
        profile.is_approved = True
        profile.save()

        if created:
            print("✅ Developer account 'flownest_dev' created successfully.")
        else:
            print("✅ Developer account 'flownest_dev' already exists - updated.")

    except Exception as e:
        print(f"Warning in migration 0024: {e}")


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0023_require_approval_for_all_non_devs'),
    ]

    operations = [
        migrations.RunPython(create_flownest_dev, migrations.RunPython.noop),
    ]
