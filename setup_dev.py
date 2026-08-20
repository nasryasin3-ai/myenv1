from django.contrib.auth.models import User
from products.models import Profile

u, _ = User.objects.get_or_create(username='flownest_dev')
u.set_password('FlowNest@2026')
u.is_superuser = True
u.is_staff = True
u.save()

p, _ = Profile.objects.get_or_create(user=u)
p.role = 'developer'
p.is_approved = True
p.is_platform_admin = True
p.company_name = 'FlowNest Core'
p.save()

print('Developer Account Ready! Username: flownest_dev | Password: FlowNest@2026')
