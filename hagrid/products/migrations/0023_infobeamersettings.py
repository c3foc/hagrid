# Generated manually for InfoBeamerSettings

from django.db import migrations, models


def create_singleton(apps, schema_editor):
    InfoBeamerSettings = apps.get_model("products", "InfoBeamerSettings")
    db_alias = schema_editor.connection.alias
    InfoBeamerSettings.objects.using(db_alias).bulk_create(
        [
            InfoBeamerSettings(),
        ]
    )


def remove_singleton(apps, schema_editor):
    from django.db import models

    InfoBeamerSettings = apps.get_model("products", "InfoBeamerSettings")
    db_alias = schema_editor.connection.alias
    try:
        models.Model.delete(InfoBeamerSettings.objects.using(db_alias).get(id=1))
    except InfoBeamerSettings.DoesNotExist:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ("products", "0022_alter_product_name"),
    ]

    operations = [
        migrations.CreateModel(
            name="InfoBeamerSettings",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "html_content",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="HTML that will be rendered on the infobeamer page (full-screen display)",
                    ),
                ),
            ],
            options={
                "verbose_name": "InfoBeamer Settings",
                "verbose_name_plural": "InfoBeamer Settings",
            },
        ),
        migrations.RunPython(create_singleton, remove_singleton),
    ]

