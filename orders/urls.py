from django.urls import path
from . import views
from django.contrib.auth.views import LogoutView

urlpatterns = [

    # =========================
    # AUTH
    # =========================
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # =========================
    # DASHBOARD
    # =========================
    path("", views.dashboard, name="dashboard"),

    # =========================
    # MASTER KATEGORI
    # =========================
    path(
        "kategori/",
        views.kategori_list,
        name="kategori_list"
    ),

    path(
        "kategori/tambah/",
        views.kategori_create,
        name="kategori_create"
    ),

    path(
        "kategori/<int:pk>/edit/",
        views.kategori_edit,
        name="kategori_edit"
    ),

    path(
        "kategori/<int:pk>/hapus/",
        views.kategori_delete,
        name="kategori_delete"
    ),

    # =========================
    # PENGGUNA
    # =========================
    path(
        "pengguna/",
        views.pengguna_list,
        name="pengguna_list"
    ),

    path(
        "pengguna/create/",
        views.pengguna_create,
        name="pengguna_create"
    ),

    path(
        "pengguna/edit/<int:pk>/",
        views.pengguna_edit,
        name="pengguna_edit"
    ),

    path(
        "pengguna/delete/<int:pk>/",
        views.pengguna_delete,
        name="pengguna_delete"
    ),

    # =========================
    # SIKLUS
    # =========================
    path('siklus/', views.siklus_list, name='siklus_list'),
    path('siklus/create/', views.siklus_create, name='siklus_create'),
    path('siklus/<int:pk>/edit/', views.siklus_edit, name='siklus_edit'),
    path('siklus/<int:pk>/delete/', views.siklus_delete, name='siklus_delete'),
    path('siklus/<int:pk>/detail/', views.siklus_detail, name='siklus_detail'),
    # Path untuk API Auto-fill
    path('api/get-resep/', views.get_resep_siklus, name='api_get_resep'),

    # =========================
    # PESANAN
    # =========================
    path("pesanan/buat/", views.create_pesanan, name="create_pesanan"),
    path("pesanan/rekap/<int:pesanan_id>/", views.rekap_pesanan, name="rekap_pesanan"),
    # path("pesanan/export/csv/<int:pesanan_id>/", views.export_csv, name="export_csv"),
    # path("pesanan/export/pdf/<int:pesanan_id>/", views.export_pdf, name="export_pdf"),

    path('pesanan/edit/<int:id>/', views.edit_pesanan, name='edit_pesanan'),
    path('pesanan/delete/<int:id>/', views.delete_pesanan, name='delete_pesanan'),
    path('pesanan/detail/<int:id>/', views.detail_pesanan_json, name='detail_pesanan_json'),
    path('pesanan/update_bahan/<int:pesanan_id>/', views.update_bahan, name='update_bahan'),
   

    # =========================
    # REKAP
    # =========================
    path("rekap/", views.rekap_pesanan, name="rekap_pesanan"),


    # =========================
    # RIWAYAT
    # =========================
    path("riwayat/", views.riwayat_pesanan, name="riwayat_pesanan"),
    path("riwayat/pdf/<int:id>/",
        views.preview_pdf_pesanan,
        name="preview_pdf_pesanan"
    ),
    path(
        'riwayat/detail/<int:id>/',
        views.detail_pesanan_json,
        name='detail_pesanan_json'
    ),
        path(
        'pesanan/delete/<int:id>/',
        views.delete_pesanan,
        name='delete_pesanan'
    ),

    # =========================
    # MASTER BAHAN
    # =========================
    path("bahan/", views.master_bahan, name="master_bahan"),
    path("bahan/tambah/", views.bahan_create, name="bahan_create"),
    path("bahan/<int:pk>/edit/", views.bahan_edit, name="bahan_edit"),
    path("bahan/<int:pk>/hapus/", views.bahan_delete, name="bahan_delete"),
]
