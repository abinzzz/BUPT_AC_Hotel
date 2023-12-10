# Generated by Django 4.1 on 2023-12-01 20:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('Air_Condition', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='room',
            name='fee_rate',
            field=models.FloatField(default=0.5, verbose_name='费率'),
        ),
        migrations.AlterField(
            model_name='scheduler',
            name='fee_rate_l',
            field=models.FloatField(default=0.3333, verbose_name='低风速费率'),
        ),
        migrations.AlterField(
            model_name='scheduler',
            name='fee_rate_m',
            field=models.FloatField(default=0.5, verbose_name='中风速费率'),
        ),
    ]
