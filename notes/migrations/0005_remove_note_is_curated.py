# Generated by Django 4.2.2 on 2023-09-09 08:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('notes', '0004_alter_note_options'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='note',
            name='is_curated',
        ),
    ]
