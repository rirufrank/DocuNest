# Generated by Django 5.2.4 on 2025-07-30 11:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0004_remove_document_file_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='is_company_wide',
            field=models.BooleanField(default=False),
        ),
    ]
