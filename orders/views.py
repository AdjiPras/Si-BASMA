import csv
import json
import logging
from datetime import timedelta
import fitz  # PyMuPDF
from io import BytesIO

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Count
from django.db.models.functions import TruncDate

from .models import Bahan, Pesanan, ItemPesanan, User, Kategori, Siklus, MenuSiklus
from urllib.parse import urlencode
from django.urls import reverse

# Inisialisasi logger
logger = logging.getLogger(__name__)

# Fungsi helper untuk render halaman error khusus
def render_error_page(request, error_message="Terjadi kesalahan pada sistem."):
    return render(request, "orders/error.html", {"error_message": error_message}, status=500)

# =========================
# AUTH
# =========================
def login_view(request):
    try:
        if request.method == "POST":
            username = request.POST.get("username")
            password = request.POST.get("password")

            user = authenticate(request, username=username, password=password)

            if user is not None:
                login(request, user)
                logger.info(f"User '{username}' berhasil login.")
                return redirect("dashboard")
            else:
                logger.warning(f"Gagal login untuk username: '{username}'")
                messages.error(request, "Username atau password salah")

        return render(request, "auth/login.html")
    except Exception as e:
        logger.error(f"Error di login_view: {e}", exc_info=True)
        return render_error_page(request, str(e))


@login_required
def logout_view(request):
    try:
        if request.method == "POST":
            username = request.user.username
            logout(request)
            logger.info(f"User '{username}' berhasil logout.")
            return redirect("login")
        return redirect("dashboard")
    except Exception as e:
        logger.error(f"Error di logout_view: {e}", exc_info=True)
        return render_error_page(request, str(e))

# Tambahkan ini di views.py
def debug_error_page(request):
    return render(request, "orders/error.html", {
        "error_message": "Silahkan hubungi Administrator"
    })


# =========================
# DASHBOARD
# =========================
@login_required
def dashboard(request):
    try:
        start_date = request.GET.get("start_date")
        end_date = request.GET.get("end_date")

        pesanan_qs = Pesanan.objects.all()
        if start_date:
            pesanan_qs = pesanan_qs.filter(created_at__date__gte=start_date)
        if end_date:
            pesanan_qs = pesanan_qs.filter(created_at__date__lte=end_date)

        today = timezone.now().date()
        seven_days_ago = today - timedelta(days=7)
        fourteen_days_ago = today - timedelta(days=14)

        def calculate_percentage(current, previous):
            if previous == 0:
                return 100.0 if current > 0 else 0.0
            return ((current - previous) / previous) * 100

        pesanan_skrg = Pesanan.objects.filter(created_at__date__gte=seven_days_ago).count()
        pesanan_lalu = Pesanan.objects.filter(created_at__date__gte=fourteen_days_ago, created_at__date__lt=seven_days_ago).count()
        
        bahan_skrg = Bahan.objects.filter(created_at__date__gte=seven_days_ago).count()
        bahan_lalu = Bahan.objects.filter(created_at__date__gte=fourteen_days_ago, created_at__date__lt=seven_days_ago).count()
        
        siklus_skrg = Siklus.objects.filter(created_at__date__gte=seven_days_ago).count()
        siklus_lalu = Siklus.objects.filter(created_at__date__gte=fourteen_days_ago, created_at__date__lt=seven_days_ago).count()

        user_skrg = User.objects.filter(date_joined__date__gte=seven_days_ago).count()
        user_lalu = User.objects.filter(date_joined__date__gte=fourteen_days_ago, date_joined__date__lt=seven_days_ago).count()

        context = {
            "total_pesanan": pesanan_qs.count(),
            "persen_pesanan": round(calculate_percentage(pesanan_skrg, pesanan_lalu), 1),
            "total_bahan": Bahan.objects.count(),
            "persen_bahan": round(calculate_percentage(bahan_skrg, bahan_lalu), 1),
            "total_siklus": Siklus.objects.count(),
            "persen_siklus": round(calculate_percentage(siklus_skrg, siklus_lalu), 1),
            "total_pengguna": User.objects.count(),
            "persen_pengguna": round(calculate_percentage(user_skrg, user_lalu), 1),
            
            "chart_labels": [item["date"].strftime("%Y-%m-%d") for item in pesanan_qs.annotate(date=TruncDate("created_at")).values("date").annotate(total=Count("id")).order_by("date") if item["date"]],
            "chart_data": [item["total"] for item in pesanan_qs.annotate(date=TruncDate("created_at")).values("date").annotate(total=Count("id")).order_by("date") if item["date"]],
            "pesanan_terbaru": Pesanan.objects.all().order_by('-id')[:6],
            "start_date": start_date,
            "end_date": end_date,
        }

        logger.info("Dashboard berhasil dimuat.")
        return render(request, "orders/dashboard.html", context)
    except Exception as e:
        logger.error(f"Error di dashboard: {e}", exc_info=True)
        return render_error_page(request, str(e))


# =========================
# MASTER KATEGORI
# =========================
@login_required
def kategori_list(request):
    try:
        q = request.GET.get('q', '')
        kategori_qs = Kategori.objects.all().order_by('nama')
        if q:
            kategori_qs = kategori_qs.filter(nama__icontains=q)
        
        paginator = Paginator(kategori_qs, 6)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'kategori_list': page_obj,
            'page_obj': page_obj,
            'q': q,
        }
        logger.info("Kategori list berhasil dimuat.")
        return render(request, 'orders/kategori_list.html', context)
    except Exception as e:
        logger.error(f"Error di kategori_list: {e}", exc_info=True)
        return render_error_page(request, str(e))


@login_required
def kategori_create(request):
    try:
        if request.method == 'POST':
            nama = request.POST.get('nama')
            Kategori.objects.create(nama=nama)
            logger.info(f"Kategori baru berhasil dibuat: '{nama}'")
            messages.success(request, 'Kategori berhasil ditambahkan!')
        return redirect('kategori_list')
    except Exception as e:
        logger.error(f"Error di kategori_create: {e}", exc_info=True)
        return render_error_page(request, str(e))


@login_required
def kategori_edit(request, pk):
    try:
        kategori = get_object_or_404(Kategori, pk=pk)
        if request.method == 'POST':
            kategori.nama = request.POST.get('nama')
            kategori.save()
            logger.info(f"Kategori ID {pk} berhasil diupdate.")
            messages.success(request, 'Kategori berhasil diupdate!')
        return redirect('kategori_list')
    except Exception as e:
        logger.error(f"Error di kategori_edit (pk={pk}): {e}", exc_info=True)
        return render_error_page(request, str(e))


@login_required
def kategori_delete(request, pk):
    try:
        kategori = get_object_or_404(Kategori, pk=pk)
        kategori.delete()
        logger.info(f"Kategori ID {pk} berhasil dihapus.")
        messages.success(request, 'Kategori berhasil dihapus!')
        return redirect('kategori_list')
    except Exception as e:
        logger.error(f"Error di kategori_delete (pk={pk}): {e}", exc_info=True)
        return render_error_page(request, str(e))


# =========================
# CREATE PESANAN
# =========================
@login_required
def create_pesanan(request):
    try:
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

            logger.info(f"Pesanan baru ID {pesanan.id} berhasil dibuat oleh {request.user.username}.")
            messages.success(request, f"Pesanan berhasil dibuat dengan {total_item} item bahan ✅")
            return redirect("riwayat_pesanan")

        return render(request, "orders/create.html", {
            "bahan_list": bahan_list,
            "siklus_list": siklus_list,
        })
    except Exception as e:
        logger.error(f"Error di create_pesanan: {e}", exc_info=True)
        return render_error_page(request, str(e))


@login_required
def detail_pesanan_json(request, id):
    try:
        pesanan = get_object_or_404(Pesanan, id=id)
        items = ItemPesanan.objects.filter(pesanan=pesanan).select_related("bahan")

        data_items = []
        for i, item in enumerate(items, start=1):
            data_items.append({
                "id": item.id,
                "no": i,
                "bahan": item.bahan.nama,
                "qty": item.qty,
                "satuan": item.bahan.satuan,
                "keterangan": item.keterangan or ''
            })

        logger.info(f"Detail pesanan JSON ID {id} berhasil diambil.")
        return JsonResponse({
            "tanggal": pesanan.tanggal_pemesanan.strftime("%Y-%m-%d"),
            "siklus": pesanan.siklus_menu.nama,
            "waktu": pesanan.waktu_makan if hasattr(pesanan, 'waktu_makan') else "-",
            "total": pesanan.jumlah_pasien or 0, 
            "user": pesanan.operator.username,
            "items": data_items
        })
    except Exception as e:
        logger.error(f"Error di detail_pesanan_json (id={id}): {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def edit_pesanan(request, id):
    try:
        pesanan = get_object_or_404(Pesanan, id=id)
        bahan_list = Bahan.objects.all()
        siklus_list = Siklus.objects.all().order_by('nama')

        if request.method == "POST":
            pesanan.tanggal_pemesanan = request.POST.get("tanggal_pemesanan")
            pesanan.siklus_menu_id = request.POST.get("siklus_menu")
            pesanan.waktu_makan = request.POST.get("waktu_makan")
            pesanan.jumlah_pasien = request.POST.get("jumlah_pasien") or 0
            pesanan.save()

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
            
            logger.info(f"Pesanan ID {id} berhasil diupdate.")
            messages.success(request, "Pesanan berhasil diupdate!")
            return redirect("riwayat_pesanan")

        items = ItemPesanan.objects.filter(pesanan=pesanan)
        return render(request, "orders/edit_pesanan.html", {
            "pesanan": pesanan,
            "items": items,
            "bahan_list": bahan_list,
            "siklus_list": siklus_list,
        })
    except Exception as e:
        logger.error(f"Error di edit_pesanan (id={id}): {e}", exc_info=True)
        return render_error_page(request, str(e))


# =========================
# RIWAYAT 
# =========================
@login_required
def riwayat_pesanan(request):
    try:
        pesanan_list = Pesanan.objects.all().order_by("-id")

        paginator = Paginator(pesanan_list, 6)
        page_number = request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        logger.info("Riwayat pesanan berhasil dimuat.")
        return render(request, "orders/riwayat.html", {
            "page_obj": page_obj
        })
    except Exception as e:
        logger.error(f"Error di riwayat_pesanan: {e}", exc_info=True)
        return render_error_page(request, str(e))


@login_required
def preview_pdf_pesanan(request, id):
    try:
        pesanan = get_object_or_404(Pesanan, id=id)
        detail_items = ItemPesanan.objects.filter(pesanan=pesanan)

        context = {
            'pesanan': pesanan,
            'detail_items': detail_items
        }
        logger.info(f"Preview PDF pesanan ID {id} berhasil dimuat.")
        return render(request, 'orders/pdf_template.html', context)
    except Exception as e:
        logger.error(f"Error di preview_pdf_pesanan (id={id}): {e}", exc_info=True)
        return render_error_page(request, str(e))


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
                continue 

        logger.info(f"Bahan untuk pesanan ID {pesanan_id} berhasil diupdate via AJAX.")
        return JsonResponse({'success': True})

    except Exception as e:
        logger.error(f"Error di update_bahan (pesanan_id={pesanan_id}): {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =========================
# REKAP PESANAN & EXPORT
# =========================
@login_required
def rekap_pesanan(request, pesanan_id):
    try:
        pesanan = get_object_or_404(Pesanan, id=pesanan_id)
        items = ItemPesanan.objects.filter(pesanan=pesanan)

        context = {
            "pesanan": pesanan,
            "items": items,
        }
        logger.info(f"Rekap pesanan ID {pesanan_id} berhasil dimuat.")
        return render(request, "orders/rekap.html", context)
    except Exception as e:
        logger.error(f"Error di rekap_pesanan (pesanan_id={pesanan_id}): {e}", exc_info=True)
        return render_error_page(request, str(e))

    
@login_required
def delete_pesanan(request, id):
    try:
        pesanan = get_object_or_404(Pesanan, id=id)
        pesanan.delete()
        logger.info(f"Pesanan ID {id} berhasil dihapus.")
        messages.success(request, "Data pesanan berhasil dihapus.")
        return redirect('riwayat_pesanan')
    except Exception as e:
        logger.error(f"Error di delete_pesanan (id={id}): {e}", exc_info=True)
        return render_error_page(request, str(e))


@login_required
def detail_pesanan_multiple_json(request):
    try:
        ids = request.GET.getlist('ids[]')
        pesanan_data = []

        for id in ids:
            pesanan = get_object_or_404(Pesanan, id=id)
            items = ItemPesanan.objects.filter(pesanan=pesanan).select_related("bahan")
            
            data_items = [{
                "bahan": item.bahan.nama,
                "qty": item.qty,
                "satuan": item.bahan.satuan,
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
            
        logger.info("Detail multiple pesanan JSON berhasil diambil.")
        return JsonResponse({"pesanan": pesanan_data})
    except Exception as e:
        logger.error(f"Error di detail_pesanan_multiple_json: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
def export_csv(request, pesanan_id):
    try:
        pesanan = get_object_or_404(Pesanan, id=pesanan_id)
        items = ItemPesanan.objects.filter(pesanan=pesanan)

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="rekap_pesanan_{pesanan_id}.csv"'

        writer = csv.writer(response)
        writer.writerow(["Bahan", "Qty"])

        for item in items:
            writer.writerow([
                item.bahan.nama,
                item.qty
            ])

        logger.info(f"Export CSV untuk pesanan ID {pesanan_id} berhasil.")
        return response
    except Exception as e:
        logger.error(f"Error di export_csv (pesanan_id={pesanan_id}): {e}", exc_info=True)
        return render_error_page(request, str(e))


@login_required
def export_pdf(request, pesanan_id):
    try:
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
        total_orang = (pesanan.jumlah_pasien or 0) + (getattr(pesanan, 'jumlah_karyawan', 0) or 0)
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
        logger.info(f"Export PDF untuk pesanan ID {pesanan_id} berhasil.")
        return FileResponse(pdf_buffer, as_attachment=False, filename=f"pesanan_{pesanan.id}.pdf")
    except Exception as e:
        logger.error(f"Error di export_pdf (pesanan_id={pesanan_id}): {e}", exc_info=True)
        return render_error_page(request, str(e))


# =========================
# MASTER BAHAN
# =========================
@login_required
def master_bahan(request):
    try:
        q = request.GET.get("q", "")
        kategori = request.GET.get("kategori", "")

        bahan_list = Bahan.objects.all().order_by("nama")

        if q:
            bahan_list = bahan_list.filter(nama__icontains=q)
        if kategori:
            bahan_list = bahan_list.filter(kategori_id=kategori)

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

        logger.info("Master bahan list berhasil dimuat.")
        return render(request, "orders/bahan_list.html", context)
    except Exception as e:
        logger.error(f"Error di master_bahan: {e}", exc_info=True)
        return render_error_page(request, str(e))


@login_required
def bahan_create(request):
    try:
        if request.method == "POST":
            nama = request.POST.get("nama")
            satuan = request.POST.get("satuan")
            kategori_id = request.POST.get("kategori")

            kategori = get_object_or_404(Kategori, id=kategori_id)
            Bahan.objects.create(
                nama=nama,
                kategori=kategori,
                satuan=satuan
            )
            logger.info(f"Bahan baru berhasil ditambahkan: '{nama}'")
            messages.success(request, 'Bahan berhasil ditambahkan!')
            return redirect("master_bahan")

        return redirect("master_bahan")
    except Exception as e:
        logger.error(f"Error di bahan_create: {e}", exc_info=True)
        return render_error_page(request, str(e))


@login_required
def bahan_edit(request, pk):
    try:
        bahan = get_object_or_404(Bahan, pk=pk)
        if request.method == "POST":
            bahan.nama = request.POST["nama"]
            kategori = get_object_or_404(Kategori, id=request.POST.get("kategori"))
            bahan.kategori = kategori
            bahan.satuan = request.POST["satuan"]
            bahan.save()
            logger.info(f"Bahan ID {pk} berhasil diupdate.")
            messages.success(request, 'Bahan berhasil diupdate!')
            return redirect("master_bahan")

        return render(request, "orders/bahan_form.html", {
            "judul": "Edit Bahan",
            "bahan": bahan,
            "kategori_choices": Kategori.objects.all()
        })
    except Exception as e:
        logger.error(f"Error di bahan_edit (pk={pk}): {e}", exc_info=True)
        return render_error_page(request, str(e))


@login_required
def bahan_delete(request, pk):
    try:
        bahan = get_object_or_404(Bahan, pk=pk)
        if request.method == "POST":
            bahan.delete()
            logger.info(f"Bahan ID {pk} berhasil dihapus.")
            messages.success(request, 'Bahan berhasil dihapus!')
            return redirect("master_bahan")
        return render(request, "orders/bahan_confirm_delete.html", {"bahan": bahan})
    except Exception as e:
        logger.error(f"Error di bahan_delete (pk={pk}): {e}", exc_info=True)
        return render_error_page(request, str(e))


# =========================
# MASTER SIKLUS
# =========================
@login_required
def siklus_list(request):
    try:
        q = request.GET.get('q', '')
        siklus_qs = Siklus.objects.all().order_by('nama')

        if q:
            siklus_qs = siklus_qs.filter(nama__icontains=q)

        paginator = Paginator(siklus_qs, 5) 
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        logger.info("Siklus list berhasil dimuat.")
        return render(request, 'orders/siklus_list.html', {
            'siklus_list': page_obj,
            'page_obj': page_obj,
            'q': q,
        })
    except Exception as e:
        logger.error(f"Error di siklus_list: {e}", exc_info=True)
        return render_error_page(request, str(e))


@login_required
def siklus_create(request):
    try:
        if request.method == 'POST':
            nama = request.POST.get('nama')
            keterangan = request.POST.get('keterangan')

            if nama:
                Siklus.objects.create(nama=nama, keterangan=keterangan)
                logger.info(f"Siklus baru berhasil dibuat: '{nama}'")
                messages.success(request, f"Siklus '{nama}' berhasil ditambahkan!")
            else:
                messages.error(request, "Gagal menambahkan siklus. Nama siklus tidak boleh kosong.")
                
        return redirect('siklus_list')
    except Exception as e:
        logger.error(f"Error di siklus_create: {e}", exc_info=True)
        return render_error_page(request, str(e))


@login_required
def siklus_edit(request, pk):
    try:
        siklus = get_object_or_404(Siklus, pk=pk)

        if request.method == 'POST':
            nama = request.POST.get('nama')
            keterangan = request.POST.get('keterangan')

            if nama:
                siklus.nama = nama
                siklus.keterangan = keterangan
                siklus.save()
                logger.info(f"Siklus ID {pk} berhasil diupdate.")
                messages.success(request, f"Siklus '{nama}' berhasil diupdate!")
            else:
                messages.error(request, "Gagal mengupdate. Nama siklus tidak boleh kosong.")

        return redirect('siklus_list')
    except Exception as e:
        logger.error(f"Error di siklus_edit (pk={pk}): {e}", exc_info=True)
        return render_error_page(request, str(e))


@login_required
def siklus_delete(request, pk):
    try:
        siklus = get_object_or_404(Siklus, pk=pk)
        nama_siklus = siklus.nama
        siklus.delete()
        
        logger.info(f"Siklus ID {pk} ('{nama_siklus}') berhasil dihapus.")
        messages.info(request, f"Siklus '{nama_siklus}' berhasil dihapus.")
        return redirect('siklus_list')
    except Exception as e:
        logger.error(f"Error di siklus_delete (pk={pk}): {e}", exc_info=True)
        return render_error_page(request, str(e))


@login_required
def siklus_detail(request, pk):
    try:
        siklus = get_object_or_404(Siklus, pk=pk)
        base_url = reverse('siklus_detail', kwargs={'pk': pk})

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
                    logger.info(f"Bahan ID {bahan_id} ditambahkan ke siklus ID {pk}.")
                    messages.success(request, f"Bahan berhasil ditambahkan ke siklus {siklus.nama}!")
                    return redirect(f"{base_url}?{urlencode({'filter_waktu': waktu})}")
                else:
                    messages.error(request, "Gagal menambahkan bahan. Pastikan semua kolom terisi.")
                return redirect(base_url)
                
            elif 'hapus_bahan' in request.POST:
                menu_id = request.POST.get('menu_id')
                menu_obj = MenuSiklus.objects.filter(id=menu_id).first()
                waktu_hapus = request.GET.get('filter_waktu') or (menu_obj.waktu_makan if menu_obj else '')
                if menu_obj:
                    menu_obj.delete()
                logger.info(f"MenuSiklus ID {menu_id} dihapus dari siklus ID {pk}.")
                messages.info(request, "Bahan berhasil dihapus.")
                if waktu_hapus:
                    return redirect(f"{base_url}?{urlencode({'filter_waktu': waktu_hapus})}")
                return redirect(base_url)
        
        filter_waktu = request.GET.get('filter_waktu')
        q = request.GET.get('q', '').strip()
        detail_qs = MenuSiklus.objects.filter(siklus=siklus)
        
        if filter_waktu:
            detail_qs = detail_qs.filter(waktu_makan=filter_waktu)
        
        if q:
            detail_qs = detail_qs.filter(bahan__nama__icontains=q)
        
        detail_qs = detail_qs.order_by('waktu_makan', 'bahan__nama')
        
        paginator = Paginator(detail_qs, 6) 
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'siklus': siklus,
            'bahan_list': Bahan.objects.all(),
            'detail_list': page_obj, 
            'page_obj': page_obj,
            'filter_waktu': filter_waktu,
            'q': q,
        }
        logger.info(f"Siklus detail ID {pk} berhasil dimuat.")
        return render(request, 'orders/siklus_detail.html', context)
    except Exception as e:
        logger.error(f"Error di siklus_detail (pk={pk}): {e}", exc_info=True)
        return render_error_page(request, str(e))

@login_required
def get_resep_siklus(request):
    try:
        siklus_id = request.GET.get('siklus_id')
        waktu_makan = request.GET.get('waktu_makan')

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
        logger.info("Resep siklus JSON berhasil diambil.")
        return JsonResponse({'success': True, 'data': data_bahan})
    except Exception as e:
        logger.error(f"Error di get_resep_siklus: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


# =========================
# PENGGUNA
# =========================
@login_required
def pengguna_list(request):
    try:
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

        logger.info("Pengguna list berhasil dimuat.")
        return render(request, "orders/pengguna_list.html", context)
    except Exception as e:
        logger.error(f"Error di pengguna_list: {e}", exc_info=True)
        return render_error_page(request, str(e))


@login_required
def pengguna_create(request):
    try:
        if request.method == "POST":
            username = request.POST.get("username")
            first_name = request.POST.get("first_name")
            last_name = request.POST.get("last_name")
            email = request.POST.get("email")
            password = request.POST.get("password")
            role = request.POST.get("role")

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

            if role == "admin":
                user.is_superuser = True
                user.is_staff = True
            elif role == "staff":
                user.is_superuser = False
                user.is_staff = True 
            else:
                user.is_superuser = False
                user.is_staff = False 

            user.save()
            logger.info(f"Pengguna baru berhasil dibuat: '{username}'")
            messages.success(request, "Pengguna berhasil ditambahkan!")
            return redirect("pengguna_list")

        return redirect("pengguna_list")
    except Exception as e:
        logger.error(f"Error di pengguna_create: {e}", exc_info=True)
        return render_error_page(request, str(e))


@login_required
def pengguna_edit(request, pk):
    try:
        pengguna = get_object_or_404(User, pk=pk)

        if request.method == "POST":
            pengguna.username = request.POST.get("username")
            pengguna.first_name = request.POST.get("first_name")
            pengguna.last_name = request.POST.get("last_name")
            pengguna.email = request.POST.get("email")
            role = request.POST.get("role")

            if request.POST.get("password"):
                pengguna.set_password(request.POST.get("password"))

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
            logger.info(f"Pengguna ID {pk} berhasil diupdate.")
            messages.success(request, "Pengguna berhasil diupdate!")
            return redirect("pengguna_list")

        return redirect("pengguna_list")
    except Exception as e:
        logger.error(f"Error di pengguna_edit (pk={pk}): {e}", exc_info=True)
        return render_error_page(request, str(e))


@login_required
def pengguna_delete(request, pk):
    try:
        pengguna = get_object_or_404(User, pk=pk)
        if request.method == "POST":
            pengguna.delete()
            logger.info(f"Pengguna ID {pk} berhasil dihapus.")
            messages.success(request, "Pengguna berhasil dihapus!")
            return redirect("pengguna_list")
        return render(request, "orders/pengguna_confirm_delete.html", {"pengguna": pengguna})
    except Exception as e:
        logger.error(f"Error di pengguna_delete (pk={pk}): {e}", exc_info=True)
        return render_error_page(request, str(e))