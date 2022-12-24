# Generated by Django 4.1.4 on 2022-12-11 23:17

from django.conf import settings
import django.contrib.auth.models
import django.contrib.auth.validators
import django.contrib.postgres.search
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
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
                    "password",
                    models.CharField(max_length=128, verbose_name="password"),
                ),
                (
                    "last_login",
                    models.DateTimeField(
                        blank=True, null=True, verbose_name="last login"
                    ),
                ),
                (
                    "is_superuser",
                    models.BooleanField(
                        default=False,
                        help_text="Designates that this user has all permissions without explicitly assigning them.",
                        verbose_name="superuser status",
                    ),
                ),
                (
                    "username",
                    models.CharField(
                        error_messages={
                            "unique": "A user with that username already exists."
                        },
                        help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.",
                        max_length=150,
                        unique=True,
                        validators=[
                            django.contrib.auth.validators.UnicodeUsernameValidator()
                        ],
                        verbose_name="username",
                    ),
                ),
                (
                    "first_name",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="first name"
                    ),
                ),
                (
                    "last_name",
                    models.CharField(
                        blank=True, max_length=150, verbose_name="last name"
                    ),
                ),
                (
                    "email",
                    models.EmailField(
                        blank=True,
                        max_length=254,
                        verbose_name="email address",
                    ),
                ),
                (
                    "is_staff",
                    models.BooleanField(
                        default=False,
                        help_text="Designates whether the user can log into this admin site.",
                        verbose_name="staff status",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.",
                        verbose_name="active",
                    ),
                ),
                (
                    "date_joined",
                    models.DateTimeField(
                        default=django.utils.timezone.now,
                        verbose_name="date joined",
                    ),
                ),
                ("location", models.CharField(max_length=250, null=True)),
                ("age", models.IntegerField(null=True)),
                ("virtual", models.BooleanField(default=False)),
                (
                    "groups",
                    models.ManyToManyField(
                        blank=True,
                        help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.group",
                        verbose_name="groups",
                    ),
                ),
                (
                    "user_permissions",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Specific permissions for this user.",
                        related_name="user_set",
                        related_query_name="user",
                        to="auth.permission",
                        verbose_name="user permissions",
                    ),
                ),
            ],
            managers=[
                ("objects", django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name="Book_Club",
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
                ("name", models.CharField(max_length=256, null=True)),
                ("virtual", models.BooleanField(default=False)),
                (
                    "members",
                    models.ManyToManyField(
                        related_name="book_clubs",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Members of the club",
                    ),
                ),
                (
                    "virtual_member",
                    models.OneToOneField(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="virtual_member_of",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Books",
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
                ("title", models.CharField(max_length=5125)),
                ("year", models.IntegerField()),
                ("authors", models.CharField(max_length=5125, null=True)),
                ("book_type", models.CharField(max_length=13)),
                ("isbn", models.CharField(max_length=13, null=True)),
                ("pages", models.IntegerField()),
                ("editions", models.IntegerField()),
                ("alt_titles", models.CharField(max_length=5125, null=True)),
                ("series_str_1", models.CharField(max_length=5125, null=True)),
                ("series_str_2", models.CharField(max_length=5125, null=True)),
                ("original_lang", models.CharField(max_length=40)),
                (
                    "original_title",
                    models.CharField(max_length=5125, null=True),
                ),
                ("original_year", models.IntegerField()),
                ("isfdb_rating", models.FloatField()),
                ("cold_start_rank", models.IntegerField(null=True)),
                ("award_winner", models.BooleanField()),
                ("juvenile", models.BooleanField()),
                ("stand_alone", models.BooleanField()),
                ("inconsistent", models.BooleanField()),
                ("virtual", models.BooleanField()),
                ("cover_image", models.CharField(max_length=5125, null=True)),
                ("wikipedia", models.CharField(max_length=20000, null=True)),
                ("synopsis", models.CharField(max_length=20000, null=True)),
                ("note", models.CharField(max_length=5125, null=True)),
                (
                    "general_search",
                    django.contrib.postgres.search.SearchVectorField(
                        null=True
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Words",
            fields=[
                (
                    "word",
                    models.CharField(
                        max_length=5125, primary_key=True, serialize=False
                    ),
                ),
                ("ndoc", models.IntegerField(null=True)),
                ("nentry", models.IntegerField(null=True)),
                ("nentry_log", models.IntegerField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name="Translations",
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
                ("title", models.CharField(max_length=5125)),
                ("year", models.IntegerField()),
                ("note", models.CharField(max_length=20000)),
                (
                    "lowest_title",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="recsys.books",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="SVDModel",
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
                ("ratings", models.IntegerField()),
                ("last_rating", models.IntegerField()),
                (
                    "time_created",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("factors", models.IntegerField()),
                ("rmse", models.FloatField()),
                ("ratings_updated", models.BooleanField(default=False)),
                ("params_bin", models.BinaryField()),
                ("model_bin", models.BinaryField()),
                (
                    "book_club",
                    models.ForeignKey(
                        db_constraint=False,
                        default=None,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="recsys.book_club",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Rating",
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
                ("rating", models.FloatField(null=True)),
                ("predicted_rating", models.FloatField(null=True)),
                (
                    "original_book_id",
                    models.CharField(max_length=1024, null=True),
                ),
                ("original_rating", models.FloatField(null=True)),
                ("original_min", models.FloatField(null=True)),
                ("original_max", models.FloatField(null=True)),
                ("saved", models.BooleanField(default=False)),
                ("blocked", models.BooleanField(default=False)),
                (
                    "last_updated",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                (
                    "book",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="recsys.books",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="More_Images",
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
                ("image", models.CharField(max_length=5125)),
                (
                    "title",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="recsys.books",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Meeting",
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
                ("date", models.DateField(null=True)),
                (
                    "book",
                    models.ForeignKey(
                        db_constraint=False,
                        null=True,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="recsys.books",
                    ),
                ),
                (
                    "book_club",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="recsys.book_club",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Isbns",
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
                ("isbn", models.CharField(max_length=13)),
                (
                    "title",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="recsys.books",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="DataProblem",
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
                ("problem", models.CharField(max_length=32768)),
                (
                    "book",
                    models.ForeignKey(
                        db_constraint=False,
                        on_delete=django.db.models.deletion.DO_NOTHING,
                        to="recsys.books",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Contents",
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
                    "book_title",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="c_contents",
                        to="recsys.books",
                    ),
                ),
                (
                    "content_title",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="c_containers",
                        to="recsys.books",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="books",
            name="containers_m2m",
            field=models.ManyToManyField(
                related_name="contents",
                related_query_name="content_title",
                through="recsys.Contents",
                to="recsys.books",
            ),
        ),
        migrations.AddField(
            model_name="books",
            name="contents_m2m",
            field=models.ManyToManyField(
                related_name="containers",
                related_query_name="container_title",
                through="recsys.Contents",
                to="recsys.books",
            ),
        ),
        migrations.AddIndex(
            model_name="svdmodel",
            index=models.Index(
                fields=["ratings"], name="recsys_svdm_ratings_e8284b_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="svdmodel",
            index=models.Index(
                fields=["last_rating"], name="recsys_svdm_last_ra_53d3c1_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="svdmodel",
            index=models.Index(
                fields=["time_created"], name="recsys_svdm_time_cr_ea1374_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="svdmodel",
            index=models.Index(
                fields=["factors"], name="recsys_svdm_factors_7004b4_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="svdmodel",
            index=models.Index(
                fields=["rmse"], name="recsys_svdm_rmse_d8a59a_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="svdmodel",
            index=models.Index(
                fields=["book_club"], name="recsys_svdm_book_cl_65c176_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="rating",
            index=models.Index(
                fields=["book"], name="recsys_rati_book_id_518aef_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="rating",
            index=models.Index(
                fields=["user"], name="recsys_rati_user_id_b5734a_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="rating",
            index=models.Index(
                fields=["rating"], name="recsys_rati_rating_5905fe_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="rating",
            index=models.Index(
                models.Func("rating", function="FLOOR"),
                name="floor_rating_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="rating",
            index=models.Index(
                fields=["predicted_rating"],
                name="recsys_rati_predict_c6b28b_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="rating",
            index=models.Index(
                models.Func("predicted_rating", function="FLOOR"),
                name="floor_predicted_rating_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="rating",
            index=models.Index(
                fields=["saved"], name="recsys_rati_saved_c7dd82_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="rating",
            index=models.Index(
                fields=["blocked"], name="recsys_rati_blocked_750ccc_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="rating",
            index=models.Index(
                fields=["last_updated"], name="recsys_rati_last_up_0eed51_idx"
            ),
        ),
        migrations.AddConstraint(
            model_name="rating",
            constraint=models.UniqueConstraint(
                fields=("book", "user"), name="OneRatingPerBookAndUser"
            ),
        ),
        migrations.AddConstraint(
            model_name="rating",
            constraint=models.CheckConstraint(
                check=models.Q(("rating__gte", 1)), name="RatingAtLeast1"
            ),
        ),
        migrations.AddConstraint(
            model_name="rating",
            constraint=models.CheckConstraint(
                check=models.Q(("rating__lte", 10)), name="RatingAtMost10"
            ),
        ),
        migrations.AddConstraint(
            model_name="rating",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("original_rating__gte", models.F("original_min"))
                ),
                name="OriginalRatingAtLeastMin",
            ),
        ),
        migrations.AddConstraint(
            model_name="rating",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("original_rating__lte", models.F("original_max"))
                ),
                name="OriginalRatingAtMostMax",
            ),
        ),
        migrations.AddIndex(
            model_name="meeting",
            index=models.Index(
                fields=["book_club"], name="recsys_meet_book_cl_0ad746_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="meeting",
            index=models.Index(
                fields=["book"], name="recsys_meet_book_id_6789a6_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="meeting",
            index=models.Index(
                fields=["date"], name="recsys_meet_date_2bc3c4_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="dataproblem",
            index=models.Index(
                fields=["book"], name="recsys_data_book_id_3e8f3f_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="dataproblem",
            index=models.Index(
                fields=["user"], name="recsys_data_user_id_ffc661_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="book_club",
            index=models.Index(
                fields=["name"], name="recsys_book_name_7d08cf_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="book_club",
            index=models.Index(
                fields=["virtual"], name="recsys_book_virtual_5362e6_idx"
            ),
        ),
        migrations.AddConstraint(
            model_name="book_club",
            constraint=models.UniqueConstraint(
                fields=("name",), name="UniqueBookClubNames"
            ),
        ),
        migrations.AddIndex(
            model_name="user",
            index=models.Index(
                fields=["username"], name="recsys_user_usernam_bbfef3_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="user",
            index=models.Index(
                fields=["first_name"], name="recsys_user_first_n_272cb6_idx"
            ),
        ),
    ]
