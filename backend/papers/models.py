import re
import uuid

from django.conf import settings
from django.db import models
from django.utils.text import slugify


def normalize_code(code):
    """'csc201', 'CSC-201', ' csc 201 ' -> 'CSC 201'."""
    compact = re.sub(r"[^A-Za-z0-9]", "", code or "").upper()
    match = re.match(r"^([A-Z]+)(\d+[A-Z]?)$", compact)
    return f"{match.group(1)} {match.group(2)}" if match else " ".join((code or "").upper().split())


class University(models.Model):
    name = models.CharField(max_length=120, unique=True)
    short_name = models.CharField(max_length=20, unique=True)  # "OAU"
    slug = models.SlugField(max_length=30, unique=True)

    class Meta:
        ordering = ["short_name"]
        verbose_name_plural = "universities"

    def save(self, *args, **kwargs):
        self.slug = self.slug or slugify(self.short_name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.short_name


class Course(models.Model):
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name="courses")
    code = models.CharField(max_length=20)  # normalised, e.g. "CSC 201"
    title = models.CharField(max_length=160)
    department = models.CharField(max_length=120, blank=True)
    level = models.PositiveSmallIntegerField(null=True, blank=True)  # 100, 200, ...
    slug = models.SlugField(max_length=60, unique=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["code"]
        constraints = [models.UniqueConstraint(fields=["university", "code"], name="unique_course_code_per_university")]

    def save(self, *args, **kwargs):
        self.code = normalize_code(self.code)
        if not self.slug:
            self.slug = slugify(f"{self.university.short_name} {self.code}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.university.short_name} {self.code}"


class Paper(models.Model):
    class Semester(models.TextChoices):
        FIRST = "first", "First semester"
        SECOND = "second", "Second semester"
        OTHER = "other", "Other"

    class Kind(models.TextChoices):
        EXAM = "exam", "Exam"
        TEST = "test", "Test"
        OTHER = "other", "Other"

    class Status(models.TextChoices):
        PROCESSING = "processing", "Reading the paper"
        READY = "ready", "Ready"
        NEEDS_TEXT = "needs_text", "Needs questions typed in"

    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="papers")
    year = models.PositiveSmallIntegerField()  # session start year, e.g. 2023 for 2023/2024
    semester = models.CharField(max_length=10, choices=Semester.choices, default=Semester.FIRST)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.EXAM)
    instructions = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="papers")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PROCESSING)
    processing_error = models.CharField(max_length=300, blank=True)
    is_hidden = models.BooleanField(default=False)  # moderators hide wrong or disputed uploads

    class Meta:
        ordering = ["-year", "semester", "kind"]
        constraints = [
            models.UniqueConstraint(fields=["course", "year", "semester", "kind"], name="unique_paper_per_sitting"),
        ]

    @property
    def session(self):
        return f"{self.year}/{self.year + 1}"

    def __str__(self):
        return f"{self.course} {self.session} {self.get_semester_display()} {self.get_kind_display()}"


def page_upload_path(instance, filename):
    return f"papers/{instance.paper.course.slug}/{instance.paper_id}/{uuid.uuid4().hex}.jpg"


class PaperPage(models.Model):
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name="pages")
    order = models.PositiveSmallIntegerField()
    image = models.ImageField(upload_to=page_upload_path)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]


class Question(models.Model):
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name="questions")
    order = models.PositiveSmallIntegerField()
    number = models.CharField(max_length=12, blank=True)  # "1a", "3(ii)"
    text = models.TextField()
    marks = models.PositiveSmallIntegerField(null=True, blank=True)
    topic = models.CharField(max_length=60, blank=True, db_index=True)

    class Meta:
        ordering = ["order"]


class Explanation(models.Model):
    """An AI-written worked answer, generated once and shared with everyone."""

    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name="explanation")
    text = models.TextField()
    model = models.CharField(max_length=80)
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    helpful = models.PositiveIntegerField(default=0)
    not_helpful = models.PositiveIntegerField(default=0)


class ExplanationVote(models.Model):
    explanation = models.ForeignKey(Explanation, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    value = models.SmallIntegerField()  # 1 helpful, -1 not helpful

    class Meta:
        constraints = [models.UniqueConstraint(fields=["explanation", "user"], name="one_vote_per_user")]


class ExplanationRequest(models.Model):
    """Log of AI explanation requests, for per-user daily limits."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)


class Flag(models.Model):
    """A report that a paper is wrong, duplicated, or shouldn't be here."""

    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name="flags")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    reason = models.CharField(max_length=300)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["paper", "user"], name="one_flag_per_user")]
