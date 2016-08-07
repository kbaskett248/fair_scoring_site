from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand, CommandError

GROUPS = [
    ('Fair runners',
     ['Can add group', 'Can add user', 'Can change user', 'Can delete user',
      'Can add judge', 'Can change judge', 'Can delete judge']),
    ('Judges',
     ['Designates this user as a judge']),
    ('Teachers',
     ['Designate this user as a teacher'])
]


class Command(BaseCommand):
    help = 'Initializes default Groups in the database'

    def handle(self, *args, **options):
        self.init_groups(GROUPS)

    def init_groups(self, groups):
        self.stdout.write('\nInitializing Groups')
        for group, perms in groups:
            grp, created = Group.objects.get_or_create(name=group)
            if created:
                self.stdout.write(self.style.SUCCESS('Successfully created Group "%s"' % grp))
            else:
                self.stdout.write(self.style.NOTICE('Group "%s" already exists' % grp))

            for perm in perms:
                permission = Permission.objects.get(name=perm)
                if permission:
                    grp.permissions.add(permission)
                    self.stdout.write(self.style.SUCCESS('\tAdded Permission "%s" to Group "%s"' % (permission, grp)))
                else:
                    self.stdout.write(self.style.NOTICE('\tNo Permission named %s' % perm))
