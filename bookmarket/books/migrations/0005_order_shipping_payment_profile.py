from django.conf import settings
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('books', '0004_review'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='order',
            options={'ordering': ['-ordered_at']},
        ),
        migrations.AddField(
            model_name='order',
            name='full_name',
            field=models.CharField(blank=True, default='', max_length=120),
        ),
        migrations.AddField(
            model_name='order',
            name='phone',
            field=models.CharField(blank=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='order',
            name='city',
            field=models.CharField(blank=True, default='', max_length=80),
        ),
        migrations.AddField(
            model_name='order',
            name='payment_method',
            field=models.CharField(choices=[('card', 'Kredi/Banka Kartı'), ('cod', 'Kapıda Ödeme')], default='card', max_length=10),
        ),
        migrations.AddField(
            model_name='order',
            name='card_last4',
            field=models.CharField(blank=True, default='', max_length=4),
        ),
        migrations.AddField(
            model_name='order',
            name='shipping_fee',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=8),
        ),
        migrations.AddField(
            model_name='order',
            name='status',
            field=models.CharField(choices=[('preparing', 'Hazırlanıyor'), ('shipped', 'Kargoya verildi'), ('in_transit', 'Dağıtımda'), ('delivered', 'Teslim edildi'), ('cancelled', 'İptal edildi')], default='preparing', max_length=12),
        ),
        migrations.AddField(
            model_name='order',
            name='carrier',
            field=models.CharField(blank=True, default='', max_length=40),
        ),
        migrations.AddField(
            model_name='order',
            name='tracking_number',
            field=models.CharField(blank=True, default='', max_length=30),
        ),
        migrations.AddField(
            model_name='order',
            name='shipped_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='order',
            name='delivered_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(blank=True, default='', max_length=20)),
                ('city', models.CharField(blank=True, default='', max_length=80)),
                ('address', models.TextField(blank=True, default='')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ShipmentEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(choices=[('preparing', 'Hazırlanıyor'), ('shipped', 'Kargoya verildi'), ('in_transit', 'Dağıtımda'), ('delivered', 'Teslim edildi'), ('cancelled', 'İptal edildi')], max_length=12)),
                ('note', models.CharField(blank=True, max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='events', to='books.order')),
            ],
            options={
                'ordering': ['created_at'],
            },
        ),
    ]
