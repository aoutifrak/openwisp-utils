# Generated by Django 4.2.3 on 2023-09-13 10:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("test_project", "0006_alter_shelf_books_count"),
    ]

    operations = [
        migrations.AddField(
            model_name="radiusaccounting",
            name="start_time",
            field=models.DateTimeField(
                blank=True, null=True, verbose_name="start time"
            ),
        ),
        migrations.AddField(
            model_name="radiusaccounting",
            name="stop_time",
            field=models.DateTimeField(blank=True, null=True, verbose_name="stop time"),
        ),
    ]
