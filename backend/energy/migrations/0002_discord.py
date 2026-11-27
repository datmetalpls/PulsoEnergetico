from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('energy', '0001_initial')]

    operations = [
        migrations.AddField(model_name='alert', name='discord_sent_at',
                            field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='session', name='discord_report_sent_at',
                            field=models.DateTimeField(blank=True, null=True)),
    ]
