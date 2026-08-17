from django.db import migrations
from django.contrib.auth.hashers import make_password


def create_developer_account(apps, schema_editor):
    """Create the FlowNest developer account with full superuser rights."""
    Profile = apps.get_model('products', 'Profile')
    User = apps.get_model('auth', 'User')

    # Create or update developer user
    dev_user, created = User.objects.get_or_create(
        username='flownest_dev',
        defaults={
            'email': 'dev@flownest.com',
            'is_staff': True,
            'is_superuser': True,
            'first_name': 'FlowNest',
            'last_name': 'Developer',
            'password': make_password('FlowNest@2026'),
        }
    )
    if not created:
        dev_user.is_staff = True
        dev_user.is_superuser = True
        dev_user.password = make_password('FlowNest@2026')
        dev_user.save()

    # Create or update developer profile
    dev_profile, _ = Profile.objects.get_or_create(user=dev_user)
    dev_profile.role = 'developer'
    dev_profile.is_approved = True
    dev_profile.is_platform_admin = True
    dev_profile.company_name = 'FlowNest Core'
    dev_profile.save()

    # Also approve all existing owners
    for profile in Profile.objects.filter(role='owner'):
        profile.is_approved = True
        profile.is_primary_owner = True
        profile.save()


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0021_approve_all_owners'),
    ]

    operations = [
        migrations.RunPython(create_developer_account, migrations.RunPython.noop),
    ]
