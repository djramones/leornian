# Generated by Django 4.2.6 on 2023-10-13 07:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0007_deattribution'),
    ]

    operations = [
        migrations.AddField(
            model_name='note',
            name='visibility_locked',
            field=models.BooleanField(default=False),
        ),
    ]
