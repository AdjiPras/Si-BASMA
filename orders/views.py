from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import HttpResponse
from django.http import JsonResponse

from .models import Bahan, Pesanan, ItemPesanan, User

import csv
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO

from django.views.decorators.csrf import csrf_exempt
from .models import ItemPesanan, Pesanan
from .models import Kategori, Siklus, MenuSiklus
from django.core.paginator import Paginator

import json

# =========================
# AUTH
# =========================
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            return redirect("dashboard")
        else:
            messages.error(request, "Username atau password salah")

    return render(request, "auth/login.html")


@login_required
def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect("login")
    return redirect("dashboard")


# =========================
# DASHBOARD
# =========================
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.shortcuts import render
from .models import Pesanan


@login_required
def dashboard(request):
    start_date = request.GET.get("start_date")
    end_date = request.GET.get("end_date")

    # base queryset pesanan
    pesanan_qs = Pesanan.objects.all()

    # filter tanggal jika ada
    if start_date:
        pesanan_qs = pesanan_qs.filter(created_at__date__gte=start_date)
    if end_date:
        pesanan_qs = pesanan_qs.filter(created_at__date__lte=end_date)

    # Menghitung total
    total_pesanan = pesanan_qs.count()
    total_bahan = Bahan.objects.count()  
    total_siklus = Siklus.objects.count() 

    # data grafik per hari (tetap untuk pesanan)
    chart_data_qs = (
        pesanan_qs
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(total=Count("id"))
        .order_by("date")
    )

    chart_labels = [
        item["date"].strftime("%Y-%m-%d") for item in chart_data_qs if item["date"]
    ]
    chart_data = [
        item["total"] for item in chart_data_qs if item["date"]
    ]

    # Ambil 5 pesanan terbaru untuk "Aktivitas Terbaru"
    pesanan_terbaru = Pesanan.objects.all().order_by('-id')[:6]

    context = {
        "total_pesanan": total_pesanan,
        "total_bahan": total_bahan,     
        "total_siklus": total_siklus,   
        "chart_labels": chart_labels,
        "chart_data": chart_data,
        "pesanan_terbaru": pesanan_terbaru,
        "start_date": start_date,
        "end_date": end_date,
    }

    return render(request, "orders/dashboard.html", context)


# =========================
# MASTER KATEGORI
# =========================
@login_required
def kategori_list(request):
    q = request.GET.get('q', '')
    kategori_qs = Kategori.objects.all().order_by('nama')
    if q:
        kategori_qs = kategori_qs.filter(
            nama__icontains=q
        )
    # PAGINATION
    paginator = Paginator(kategori_qs, 6)  # 10 per halaman
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'kategori_list': page_obj,  # penting: ganti ini
        'page_obj': page_obj,
        'q': q,
    }
    return render(request, 'orders/kategori_list.html', context)


@login_required
def kategori_create(request):
    if request.method == 'POST':
        nama = request.POST.get('nama')
        Kategori.objects.create(nama=nama)
        messages.success(request, 'Kategori berhasil ditambahkan!')
    return redirect('kategori_list')

@login_required
def kategori_edit(request, pk):
    kategori = get_object_or_404(Kategori, pk=pk)
    if request.method == 'POST':
        kategori.nama = request.POST.get('nama')
        kategori.save()
        messages.success(request, 'Kategori berhasil diupdate!')
    return redirect('kategori_list')

@login_required
def kategori_delete(request, pk):
    kategori = get_object_or_404(Kategori, pk=pk)
    kategori.delete()
    messages.success(request, 'Kategori berhasil dihapus!')
    return redirect('kategori_list')


# =========================
# CREATE PESANAN
# =========================
from django.contrib import messages
from django.contrib.auth.decorators import login_required

@login_required
def create_pesanan(request):

    bahan_list = Bahan.objects.all()
    siklus_list = Siklus.objects.all().order_by('nama')

    if request.method == "POST":

        pesanan = Pesanan.objects.create(
            operator=request.user,
            tanggal_pemesanan=request.POST.get("tanggal_pemesanan"),
            siklus_menu_id=request.POST.get("siklus_menu"),
            waktu_makan=request.POST.get("waktu_makan"),
            jumlah_pasien=request.POST.get("jumlah_pasien") or 0,
        )

        bahan_ids = request.POST.getlist("bahan[]")
        qtys = request.POST.getlist("qty[]")
        keterangans = request.POST.getlist("keterangan[]")

        total_item = 0

        for bahan_id, qty, keterangan in zip(bahan_ids, qtys, keterangans):

            if qty and float(qty) > 0:

                ItemPesanan.objects.create(
                    pesanan=pesanan,
                    bahan_id=bahan_id,
                    qty=qty,
                    keterangan=keterangan
                )

                total_item += 1

        messages.success(
            request,
            f"Pesanan berhasil dibuat dengan {total_item} item bahan ✅"
        )

        return redirect("riwayat_pesanan")

    return render(request, "orders/create.html", {
        "bahan_list": bahan_list,
        "siklus_list": siklus_list,
    })


@login_required
def detail_pesanan_json(request, id):
    pesanan = get_object_or_404(Pesanan, id=id)
    items = ItemPesanan.objects.filter(pesanan=pesanan)

    data_items = []
    for i, item in enumerate(items, start=1):
        data_items.append({
            "id": item.id,
            "no": i,
            "bahan": item.bahan.nama,
            "qty": item.qty,
            "keterangan": item.keterangan or ''
        })

    return JsonResponse({
        "tanggal": pesanan.tanggal_pemesanan.strftime("%Y-%m-%d"),
        "siklus": pesanan.siklus_menu.nama,
        "waktu": pesanan.waktu_makan if hasattr(pesanan, 'waktu_makan') else "-",
        "total": pesanan.jumlah_pasien or 0, 
        "user": pesanan.operator.username,
        "items": data_items
    })

# @login_required
# def edit_pesanan(request, id):
#     pesanan = get_object_or_404(Pesanan, id=id)

#     if request.method == 'POST':
#         pesanan.tanggal_pemesanan = request.POST.get('tanggal_pemesanan')
#         pesanan.siklus_menu = request.POST.get('siklus_menu')
#         pesanan.jumlah_pasien = request.POST.get('jumlah_pasien')
#         pesanan.jumlah_karyawan = request.POST.get('jumlah_karyawan')
#         pesanan.save()

#     return redirect('riwayat_pesanan')

@login_required
def edit_pesanan(request, id):
    pesanan = get_object_or_404(Pesanan, id=id)
    bahan_list = Bahan.objects.all()
    siklus_list = Siklus.objects.all().order_by('nama')

    if request.method == "POST":
        # 1. Update data utama pesanan
        pesanan.tanggal_pemesanan = request.POST.get("tanggal_pemesanan")
        pesanan.siklus_menu_id = request.POST.get("siklus_menu")
        pesanan.waktu_makan = request.POST.get("waktu_makan")
        pesanan.jumlah_pasien = request.POST.get("jumlah_pasien") or 0
        pesanan.save()

        # 2. Hapus semua item lama dan buat baru (Cara paling aman & mudah)
        ItemPesanan.objects.filter(pesanan=pesanan).delete()

        bahan_ids = request.POST.getlist("bahan[]")
        qtys = request.POST.getlist("qty[]")
        keterangans = request.POST.getlist("keterangan[]")

        for bahan_id, qty, keterangan in zip(bahan_ids, qtys, keterangans):
            if qty and float(qty) > 0:
                ItemPesanan.objects.create(
                    pesanan=pesanan,
                    bahan_id=bahan_id,
                    qty=qty,
                    keterangan=keterangan
                )
        
        messages.success(request, "Pesanan berhasil diupdate!")
        return redirect("riwayat_pesanan")

    # Ambil items untuk ditampilkan di form
    items = ItemPesanan.objects.filter(pesanan=pesanan)
    
    return render(request, "orders/edit_pesanan.html", {
        "pesanan": pesanan,
        "items": items,
        "bahan_list": bahan_list,
        "siklus_list": siklus_list,
    })


@login_required
def delete_pesanan(request, id):
    pesanan = get_object_or_404(Pesanan, id=id)

    if request.method == "POST":
        pesanan.delete()

    return redirect('riwayat_pesanan')




# =========================
# RIWAYAT 
# =========================
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required

@login_required
def riwayat_pesanan(request):
    pesanan_list = Pesanan.objects.all().order_by("-id")

    paginator = Paginator(pesanan_list, 6)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "orders/riwayat.html", {
        "page_obj": page_obj
    })

from django.shortcuts import render, get_object_or_404
from .models import Pesanan, ItemPesanan

@login_required
def preview_pdf_pesanan(request, id):
    pesanan = get_object_or_404(Pesanan, id=id)
    detail_items = ItemPesanan.objects.filter(pesanan=pesanan)

    context = {
        'pesanan': pesanan,
        'detail_items': detail_items
    }
    return render(request, 'orders/pdf_template.html', context)


@login_required
@csrf_exempt
def update_bahan(request, pesanan_id):
    if request.method != "POST":
        return JsonResponse({'success': False, 'error': 'Metode harus POST'})

    try:
        data = json.loads(request.body)
        items = data.get('items', [])

        for item in items:
            item_id = item.get('id')
            if not item_id:
                continue

            try:
                item_obj = ItemPesanan.objects.get(id=item_id, pesanan_id=pesanan_id)
                item_obj.qty = float(item.get('qty', 0))
                item_obj.keterangan = item.get('keterangan', '')
                item_obj.save()
            except ItemPesanan.DoesNotExist:
                continue  # skip jika tidak ditemukan

        return JsonResponse({'success': True})

    except Exception as e:
        print("Update bahan error:", e)
        return JsonResponse({'success': False, 'error': str(e)})


# =========================
# REKAP PESANAN
# =========================
@login_required
def rekap_pesanan(request, pesanan_id):
    pesanan = get_object_or_404(Pesanan, id=pesanan_id)
    items = ItemPesanan.objects.filter(pesanan=pesanan)

    context = {
        "pesanan": pesanan,
        "items": items,
    }
    return render(request, "orders/rekap.html", context)

    
@login_required
def delete_pesanan(request, id):
    pesanan = get_object_or_404(Pesanan, id=id)

    pesanan.delete()

    messages.success(request, "Data pesanan berhasil dihapus.")

    return redirect('riwayat_pesanan')

@login_required
def detail_pesanan_multiple_json(request):
    # Mengambil list ID dari query parameter
    ids = request.GET.getlist('ids[]')
    pesanan_data = []

    for id in ids:
        pesanan = get_object_or_404(Pesanan, id=id)
        items = ItemPesanan.objects.filter(pesanan=pesanan)
        
        data_items = [{
            "bahan": item.bahan.nama,
            "qty": item.qty,
            "keterangan": item.keterangan or '-'
        } for item in items]

        pesanan_data.append({
            "id": pesanan.id,
            "tanggal": pesanan.tanggal_pemesanan.strftime("%Y-%m-%d"),
            "siklus": pesanan.siklus_menu.nama if pesanan.siklus_menu else "-",
            "waktu": pesanan.waktu_makan,
            "total": pesanan.jumlah_pasien or 0,
            "user": pesanan.operator.username,
            "items": data_items
        })
        
    return JsonResponse({"pesanan": pesanan_data})
# =========================
# EXPORT CSV
# =========================
@login_required
def export_csv(request, pesanan_id):
    pesanan = get_object_or_404(Pesanan, id=pesanan_id)
    items = ItemPesanan.objects.filter(pesanan=pesanan)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="rekap_pesanan_{pesanan_id}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(["Bahan", "Qty"])

    for item in items:
        writer.writerow([
            item.bahan.nama,
            item.qty
        ])

    return response


# =========================
# EXPORT PDF
# =========================
# views.py
import fitz  # PyMuPDF
from io import BytesIO
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Pesanan, ItemPesanan

@login_required
def export_pdf(request, pesanan_id):
    pesanan = get_object_or_404(Pesanan, id=pesanan_id)
    items = ItemPesanan.objects.filter(pesanan=pesanan)

    pdf_buffer = BytesIO()
    doc = fitz.open()
    page = doc.new_page()
    x, y = 50, 50
    line_height = 20

    page.insert_text((x, y), f"Detail Pesanan ID: {pesanan.id}", fontsize=14)
    y += line_height
    page.insert_text((x, y), f"Tanggal: {pesanan.tanggal_pemesanan}", fontsize=12)
    y += line_height
    page.insert_text((x, y), f"Siklus: {pesanan.siklus_menu}", fontsize=12)
    y += line_height
    total_orang = (pesanan.jumlah_pasien or 0) + (pesanan.jumlah_karyawan or 0)
    page.insert_text((x, y), f"Total Orang: {total_orang}", fontsize=12)
    y += line_height
    page.insert_text((x, y), f"Operator: {pesanan.operator.username}", fontsize=12)
    y += line_height * 2

    page.insert_text((x, y), f"{'No':<5}{'Bahan':<25}{'Qty':<10}{'Keterangan'}", fontsize=12)
    y += line_height

    for i, item in enumerate(items, start=1):
        page.insert_text((x, y), f"{i:<5}{item.bahan.nama:<25}{item.qty:<10}{item.keterangan or ''}", fontsize=12)
        y += line_height
        if y > 700:
            page = doc.new_page()
            y = 50

    doc.save(pdf_buffer)
    pdf_buffer.seek(0)
    return FileResponse(pdf_buffer, as_attachment=False, filename=f"pesanan_{pesanan.id}.pdf")


# =========================
# MASTER BAHAN
# =========================
@login_required
def master_bahan(request):

    q = request.GET.get("q", "")
    kategori = request.GET.get("kategori", "")

    bahan_list = Bahan.objects.all().order_by("nama")

    if q:
        bahan_list = bahan_list.filter(
            nama__icontains=q
        )

    if kategori:
        bahan_list = bahan_list.filter(
            kategori_id=kategori
        )

    # PAGINATION
    paginator = Paginator(bahan_list, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "bahan_list": page_obj,
        "kategori_choices": Kategori.objects.all(),
        "q": q,
        "kategori_aktif": kategori
    }

    return render(
        request,
        "orders/bahan_list.html",
        context
    )

@login_required
def bahan_create(request):

    if request.method == "POST":

        nama = request.POST.get("nama")
        satuan = request.POST.get("satuan")
        kategori_id = request.POST.get("kategori")

        kategori = get_object_or_404(
            Kategori,
            id=kategori_id
        )

        Bahan.objects.create(
            nama=nama,
            kategori=kategori,
            satuan=satuan
        )
        messages.success(request, 'Bahan berhasil ditambahkan!')
        return redirect("master_bahan")

    return redirect("master_bahan")

@login_required
def bahan_edit(request, pk):

    bahan = get_object_or_404(Bahan, pk=pk)
    if request.method == "POST":
        bahan.nama = request.POST["nama"]
        kategori = get_object_or_404(
            Kategori,
            id=request.POST.get("kategori")
        )
        bahan.kategori = kategori
        bahan.satuan = request.POST["satuan"]
        bahan.save()
        messages.success(request, 'Bahan berhasil diupdate!')
        return redirect("master_bahan")

    return render(request, "orders/bahan_form.html", {
        "judul": "Edit Bahan",
        "bahan": bahan,
        "kategori_choices": Kategori.objects.all()
    })

@login_required
def bahan_delete(request, pk):
    bahan = get_object_or_404(Bahan, pk=pk)

    if request.method == "POST":
        bahan.delete()
        messages.success(request, 'Bahan berhasil dihapus!')
        return redirect("master_bahan")
    return render(request, "orders/bahan_confirm_delete.html", {
        "bahan": bahan
    })

# =========================
# MASTER SIKLUS
# =========================
@login_required
def siklus_list(request):

    q = request.GET.get('q', '')

    siklus_qs = Siklus.objects.all().order_by('nama')

    if q:
        siklus_qs = siklus_qs.filter(
            nama__icontains=q
        )

    # PAGINATION
    paginator = Paginator(siklus_qs, 5) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'orders/siklus_list.html', {
        'siklus_list': page_obj,
        'page_obj': page_obj,
        'q': q,
    })


@login_required
def siklus_create(request):
    if request.method == 'POST':
        nama = request.POST.get('nama')
        keterangan = request.POST.get('keterangan')

        # Validasi sederhana: pastikan nama tidak kosong
        if nama:
            Siklus.objects.create(
                nama=nama,
                keterangan=keterangan
            )
            messages.success(request, f"Siklus '{nama}' berhasil ditambahkan!")
        else:
            messages.error(request, "Gagal menambahkan siklus. Nama siklus tidak boleh kosong.")
            
    # Selalu redirect, baik setelah POST sukses atau jika bukan POST
    return redirect('siklus_list')


@login_required
def siklus_edit(request, pk):
    siklus = get_object_or_404(Siklus, pk=pk)

    if request.method == 'POST':
        nama = request.POST.get('nama')
        keterangan = request.POST.get('keterangan')

        if nama:
            siklus.nama = nama
            siklus.keterangan = keterangan
            siklus.save()
            messages.success(request, f"Siklus '{nama}' berhasil diupdate!")
        else:
            messages.error(request, "Gagal mengupdate. Nama siklus tidak boleh kosong.")

    return redirect('siklus_list')


@login_required
def siklus_delete(request, pk):
    siklus = get_object_or_404(Siklus, pk=pk)
    
    # Simpan nama untuk pesan notifikasi
    nama_siklus = siklus.nama
    siklus.delete()
    
    messages.info(request, f"Siklus '{nama_siklus}' berhasil dihapus.")
    return redirect('siklus_list')

# ============================
# DETAIL SIKLUS
# ============================
@login_required
def siklus_detail(request, pk):
    siklus = get_object_or_404(Siklus, pk=pk)
    
    # 1. LOGIKA POST: Manipulasi Data
    if request.method == "POST":
        if 'tambah_bahan' in request.POST:
            bahan_id = request.POST.get('bahan_id')
            waktu = request.POST.get('waktu_makan')
            qty = request.POST.get('qty')
            
            if bahan_id and waktu and qty:
                MenuSiklus.objects.create(
                    siklus=siklus,
                    bahan_id=bahan_id,
                    waktu_makan=waktu,
                    qty_standar=qty
                )
                messages.success(request, f"Bahan berhasil ditambahkan ke siklus {siklus.nama}!")
            else:
                messages.error(request, "Gagal menambahkan bahan. Pastikan semua kolom terisi.")
            return redirect('siklus_detail', pk=pk)
            
        elif 'hapus_bahan' in request.POST:
            menu_id = request.POST.get('menu_id')
            MenuSiklus.objects.filter(id=menu_id).delete()
            messages.info(request, "Bahan berhasil dihapus.")
            return redirect('siklus_detail', pk=pk)
    
    # 2. LOGIKA GET: Pengambilan Data Terfilter
    filter_waktu = request.GET.get('filter_waktu')
    detail_qs = MenuSiklus.objects.filter(siklus=siklus)
    
    if filter_waktu:
        detail_qs = detail_qs.filter(waktu_makan=filter_waktu)
    
    detail_qs = detail_qs.order_by('waktu_makan', 'bahan__nama')
    
    # 3. PAGINASI: 6 item per halaman
    paginator = Paginator(detail_qs, 6) 
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 4. KONTEKS
    context = {
        'siklus': siklus,
        'bahan_list': Bahan.objects.all(),
        'detail_list': page_obj, 
        'page_obj': page_obj,
        'filter_waktu': filter_waktu,
    }
    return render(request, 'orders/siklus_detail.html', context)


# =========================
# API UNTUK AUTO-FILL RESEP
# =========================
@login_required
def get_resep_siklus(request):
    siklus_id = request.GET.get('siklus_id')
    waktu_makan = request.GET.get('waktu_makan')

    # Gunakan filter yang menangani case-insensitive agar tidak error kapital/kecil
    resep_list = MenuSiklus.objects.filter(
        siklus_id=siklus_id, 
        waktu_makan__iexact=waktu_makan 
    )

    data_bahan = [
        {
            'bahan_id': resep.bahan.id,
            'bahan_nama': resep.bahan.nama,
            'satuan': resep.bahan.satuan,
            'qty_standar': resep.qty_standar
        } for resep in resep_list
    ]
    return JsonResponse({'success': True, 'data': data_bahan})


@login_required
def kelola_menu_siklus(request, siklus_id):
    siklus = get_object_or_404(Siklus, id=siklus_id)
    
    if request.method == 'POST':
        # LOGIKA TAMBAH
        if 'tambah_bahan' in request.POST:
            bahan_id = request.POST.get('bahan')
            qty = request.POST.get('qty')
            waktu = request.POST.get('waktu_makan')
            
            MenuSiklus.objects.create(
                siklus=siklus,
                bahan_id=bahan_id,
                qty_standar=qty,
                waktu_makan=waktu
            )
            messages.success(request, "Bahan berhasil ditambahkan.")
            return redirect('kelola_menu_siklus', siklus_id=siklus_id)

        # LOGIKA HAPUS
        elif 'hapus_menu' in request.POST:
            menu_id = request.POST.get('menu_id')
            MenuSiklus.objects.filter(id=menu_id).delete()
            messages.info(request, "Menu siklus berhasil dihapus.")
            return redirect('kelola_menu_siklus', siklus_id=siklus_id)
    
    # Menampilkan data
    context = {
        'siklus': siklus, 
        'bahan_list': Bahan.objects.all().order_by('nama'),
        'detail_list': MenuSiklus.objects.filter(siklus=siklus).order_by('waktu_makan', 'bahan__nama')
    }
    return render(request, 'siklus_detail.html', context)


# =========================
# PENGGUNA
# =========================
@login_required
def pengguna_list(request):
    q = request.GET.get("q", "")
    pengguna_list = User.objects.all().order_by("username")

    if q:
        pengguna_list = pengguna_list.filter(
            username__icontains=q
        ) | User.objects.filter(
            first_name__icontains=q
        ) | User.objects.filter(
            last_name__icontains=q
        ) | User.objects.filter(
            email__icontains=q
        )

    paginator = Paginator(pengguna_list, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "pengguna_list": page_obj,
        "q": q
    }

    return render(request, "orders/pengguna_list.html", context)


@login_required
def pengguna_create(request):
    if request.method == "POST":
        username = request.POST.get("username")
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        role = request.POST.get("role") # 'admin', 'staff', atau 'operator'

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username sudah digunakan!")
            return redirect("pengguna_list")

        user = User.objects.create_user(
            username=username,
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password
        )

        # Atur hak akses berdasarkan pilihan kolom role biasa
        if role == "admin":
            user.is_superuser = True
            user.is_staff = True
        elif role == "staff":
            user.is_superuser = False
            user.is_staff = True # Level staf di bawah superuser
        else:
            user.is_superuser = False
            user.is_staff = False # User biasa / Operator

        user.save()

        messages.success(request, "Pengguna berhasil ditambahkan!")
        return redirect("pengguna_list")

    return redirect("pengguna_list")


@login_required
def pengguna_edit(request, pk):
    pengguna = get_object_or_404(User, pk=pk)

    if request.method == "POST":
        pengguna.username = request.POST.get("username")
        pengguna.first_name = request.POST.get("first_name")
        pengguna.last_name = request.POST.get("last_name")
        pengguna.email = request.POST.get("email")
        role = request.POST.get("role")

        if request.POST.get("password"):
            pengguna.set_password(request.POST.get("password"))

        # Update hak akses level menu
        if role == "admin":
            pengguna.is_superuser = True
            pengguna.is_staff = True
        elif role == "staff":
            pengguna.is_superuser = False
            pengguna.is_staff = True
        else:
            pengguna.is_superuser = False
            pengguna.is_staff = False

        pengguna.save()

        messages.success(request, "Pengguna berhasil diupdate!")
        return redirect("pengguna_list")

    return redirect("pengguna_list")


@login_required
def pengguna_delete(request, pk):
    pengguna = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        pengguna.delete()
        messages.success(request, "Pengguna berhasil dihapus!")
        return redirect("pengguna_list")
    return render(
        request,
        "orders/pengguna_confirm_delete.html",
        {
            "pengguna": pengguna
        }
    )