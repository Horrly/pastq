from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path

from papers import views as p

from .views import health, spa

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/health/", health, name="health"),
    path("api/auth/", include("accounts.urls")),
    path("api/config/", p.ConfigView.as_view()),
    path("api/stats/", p.StatsView.as_view()),
    path("api/universities/", p.UniversityListView.as_view()),
    path("api/courses/", p.CourseListView.as_view()),
    path("api/courses/<slug:slug>/", p.CourseDetailView.as_view()),
    path("api/courses/<slug:slug>/practice/", p.PracticeView.as_view()),
    path("api/papers/", p.PaperUploadView.as_view()),
    path("api/papers/<int:pk>/", p.PaperDetailView.as_view()),
    path("api/papers/<int:pk>/questions/", p.PaperQuestionsView.as_view()),
    path("api/papers/<int:pk>/retry/", p.PaperRetryView.as_view()),
    path("api/papers/<int:pk>/flag/", p.PaperFlagView.as_view()),
    path("api/questions/<int:pk>/explain/", p.ExplainView.as_view()),
    path("api/explanations/<int:pk>/vote/", p.VoteView.as_view()),
]

# Local file storage (development). In production files come from S3-compatible storage.
if not settings.S3_BUCKET:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    if not settings.DEBUG:  # static() is a no-op without DEBUG; serve media explicitly
        from django.views.static import serve
        urlpatterns += [re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT})]

urlpatterns += [re_path(r"^(?!api/|admin/|static/|media/).*$", spa, name="spa")]
