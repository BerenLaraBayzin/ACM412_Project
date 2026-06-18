from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('books', '0005_order_shipping_payment_profile'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='is_read',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='book',
            name='views_count',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
