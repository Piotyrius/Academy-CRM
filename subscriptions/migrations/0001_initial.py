# Generated migration for subscriptions app

import uuid
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text='Organization/Academy name', max_length=200)),
                ('domain', models.CharField(blank=True, help_text='Subdomain for this organization (e.g., "academy1" for academy1.yourdomain.com)', max_length=100, null=True, unique=True)),
                ('status', models.CharField(choices=[('ACTIVE', 'Active'), ('SUSPENDED', 'Suspended'), ('TRIAL', 'Trial'), ('INACTIVE', 'Inactive')], default='TRIAL', help_text='Organization status', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('trial_ends_at', models.DateTimeField(blank=True, help_text='Trial expiration date', null=True)),
            ],
            options={
                'verbose_name': 'organization',
                'verbose_name_plural': 'organizations',
                'db_table': 'organizations',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='SubscriptionPlan',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text='Plan name (e.g., Basic, Pro, Enterprise)', max_length=100, unique=True)),
                ('description', models.TextField(blank=True, help_text='Plan description')),
                ('price', models.DecimalField(decimal_places=2, help_text='Monthly price', max_digits=10)),
                ('billing_cycle', models.CharField(choices=[('MONTHLY', 'Monthly'), ('QUARTERLY', 'Quarterly'), ('YEARLY', 'Yearly')], default='MONTHLY', help_text='Billing cycle', max_length=20)),
                ('is_active', models.BooleanField(default=True, help_text='Is this plan currently available?')),
                ('max_users', models.IntegerField(blank=True, help_text='Maximum number of users (null = unlimited)', null=True)),
                ('max_students', models.IntegerField(blank=True, help_text='Maximum number of students (null = unlimited)', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'subscription plan',
                'verbose_name_plural': 'subscription plans',
                'db_table': 'subscription_plans',
                'ordering': ['price'],
            },
        ),
        migrations.CreateModel(
            name='Subscription',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('ACTIVE', 'Active'), ('TRIAL', 'Trial'), ('EXPIRED', 'Expired'), ('CANCELLED', 'Cancelled'), ('SUSPENDED', 'Suspended')], default='TRIAL', help_text='Subscription status', max_length=20)),
                ('start_date', models.DateTimeField(auto_now_add=True, help_text='Subscription start date')),
                ('end_date', models.DateTimeField(blank=True, help_text='Subscription end date (null = ongoing)', null=True)),
                ('trial_ends_at', models.DateTimeField(blank=True, help_text='Trial expiration date', null=True)),
                ('auto_renew', models.BooleanField(default=True, help_text='Auto-renew subscription?')),
                ('cancelled_at', models.DateTimeField(blank=True, help_text='Cancellation date', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('organization', models.OneToOneField(help_text='Organization this subscription belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='subscription', to='subscriptions.organization')),
                ('plan', models.ForeignKey(help_text='Subscription plan', on_delete=django.db.models.deletion.PROTECT, related_name='subscriptions', to='subscriptions.subscriptionplan')),
            ],
            options={
                'verbose_name': 'subscription',
                'verbose_name_plural': 'subscriptions',
                'db_table': 'subscriptions',
            },
        ),
        migrations.CreateModel(
            name='PlanFeature',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('module_name', models.CharField(help_text='Module name (e.g., attendance, assessment, timekeeping)', max_length=50)),
                ('enabled', models.BooleanField(default=True, help_text='Is this feature enabled for this plan?')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('plan', models.ForeignKey(help_text='Subscription plan', on_delete=django.db.models.deletion.CASCADE, related_name='features', to='subscriptions.subscriptionplan')),
            ],
            options={
                'verbose_name': 'plan feature',
                'verbose_name_plural': 'plan features',
                'db_table': 'plan_features',
                'unique_together': {('plan', 'module_name')},
            },
        ),
        migrations.CreateModel(
            name='Billing',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('amount', models.DecimalField(decimal_places=2, help_text='Billing amount', max_digits=10)),
                ('status', models.CharField(choices=[('PENDING', 'Pending'), ('PAID', 'Paid'), ('FAILED', 'Failed'), ('REFUNDED', 'Refunded')], default='PENDING', help_text='Payment status', max_length=20)),
                ('payment_date', models.DateTimeField(blank=True, help_text='Payment date', null=True)),
                ('due_date', models.DateTimeField(help_text='Payment due date')),
                ('invoice_number', models.CharField(blank=True, help_text='Invoice number', max_length=50, null=True, unique=True)),
                ('payment_method', models.CharField(blank=True, help_text='Payment method (e.g., credit_card, paypal, bank_transfer)', max_length=50)),
                ('notes', models.TextField(blank=True, help_text='Additional notes')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('organization', models.ForeignKey(help_text='Organization this billing belongs to', on_delete=django.db.models.deletion.CASCADE, related_name='billings', to='subscriptions.organization')),
                ('subscription', models.ForeignKey(help_text='Subscription this billing is for', on_delete=django.db.models.deletion.CASCADE, related_name='billings', to='subscriptions.subscription')),
            ],
            options={
                'verbose_name': 'billing',
                'verbose_name_plural': 'billings',
                'db_table': 'billings',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='organization',
            index=models.Index(fields=['domain'], name='organizations_domain_idx'),
        ),
        migrations.AddIndex(
            model_name='organization',
            index=models.Index(fields=['status'], name='organizations_status_idx'),
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['organization'], name='subscriptions_organization_idx'),
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['status'], name='subscriptions_status_idx'),
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(fields=['end_date'], name='subscriptions_end_date_idx'),
        ),
        migrations.AddIndex(
            model_name='planfeature',
            index=models.Index(fields=['plan', 'module_name'], name='plan_features_plan_module_idx'),
        ),
        migrations.AddIndex(
            model_name='billing',
            index=models.Index(fields=['organization'], name='billings_organization_idx'),
        ),
        migrations.AddIndex(
            model_name='billing',
            index=models.Index(fields=['status'], name='billings_status_idx'),
        ),
        migrations.AddIndex(
            model_name='billing',
            index=models.Index(fields=['due_date'], name='billings_due_date_idx'),
        ),
    ]

