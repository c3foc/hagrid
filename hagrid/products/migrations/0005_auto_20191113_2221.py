# Generated by Django 2.2.4 on 2019-11-13 21:21

from django.db import migrations
import positions.fields


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0004_auto_20191113_1926_squashed_0007_auto_20191113_1937'),
    ]

    operations = [
        migrations.AlterField(
            model_name='product',
            name='position',
            field=positions.fields.PositionField(default=-1),
        ),
        migrations.AlterField(
            model_name='size',
            name='position',
            field=positions.fields.PositionField(default=-1),
        ),
    ]