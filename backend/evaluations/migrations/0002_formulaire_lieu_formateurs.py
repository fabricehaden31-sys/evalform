from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('evaluations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='formulaire',
            name='lieu',
            field=models.CharField(blank=True, default='', max_length=200),
        ),
        migrations.AddField(
            model_name='formulaire',
            name='formateurs',
            field=models.CharField(blank=True, default='', max_length=400),
        ),
    ]
