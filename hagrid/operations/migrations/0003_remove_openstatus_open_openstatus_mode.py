# Generated by Django 4.2.16 on 2024-12-06 08:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("operations", "0002_alter_openstatus_options"),
    ]

    operations = [
        migrations.AddField(
            model_name="openstatus",
            name="mode",
            field=models.CharField(
                choices=[
                    ("closed", "Closed"),
                    ("open", "Open"),
                    ("presale", "Presale pickup"),
                ],
                default="closed",
                max_length=7,
            ),
        ),
        migrations.RunSQL(
            "UPDATE operations_openstatus SET mode = CASE open WHEN true THEN 'open' ELSE 'closed' END;",
            "UPDATE operations_openstatus SET open = CASE mode WHEN 'closed' THEN false ELSE true END;"
        ),
        migrations.RemoveField(
            model_name="openstatus",
            name="open",
        ),
    ]