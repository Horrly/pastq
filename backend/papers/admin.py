from django.contrib import admin

from .models import Course, Explanation, Flag, Paper, PaperPage, Question, University


@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ["short_name", "name"]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["code", "title", "university", "level"]
    list_filter = ["university"]
    search_fields = ["code", "title"]


class PageInline(admin.TabularInline):
    model = PaperPage
    extra = 0


class QuestionInline(admin.StackedInline):
    model = Question
    extra = 0


@admin.register(Paper)
class PaperAdmin(admin.ModelAdmin):
    list_display = ["__str__", "status", "uploaded_by", "is_hidden", "created_at"]
    list_filter = ["status", "is_hidden", "course__university"]
    list_editable = ["is_hidden"]
    inlines = [PageInline, QuestionInline]


@admin.register(Flag)
class FlagAdmin(admin.ModelAdmin):
    list_display = ["paper", "user", "reason", "resolved", "created_at"]
    list_filter = ["resolved"]
    list_editable = ["resolved"]


@admin.register(Explanation)
class ExplanationAdmin(admin.ModelAdmin):
    list_display = ["question", "helpful", "not_helpful", "model", "created_at"]
