from django.db import models
from django.contrib.auth.models import User


# =========================
# MASTER BAHAN
# =========================
class Bahan(models.Model):
    # KATEGORI_CHOICES = [
    #     ("Karbohidrat", "Karbohidrat"),
    #     ("Protein", "Protein"),
    #     ("Protein Nabati", "Protein Nabati"),
    #     ("Sayuran", "Sayuran"),
    #     ("Bumbu", "Bumbu"),
    #     ("Minyak", "Minyak"),
    # ]

    nama = models.CharField(
        max_length=200,
        verbose_name="Nama Bahan"
    )
    kategori = models.ForeignKey(
        'Kategori',
        on_delete=models.CASCADE,
        related_name='bahan'
    )
    satuan = models.CharField(
        max_length=50,
        verbose_name="Satuan"
    )

    def __str__(self):
        return f"{self.nama} ({self.satuan})"
    
# =========================
# MASTER KATEGORI
# =========================
class Kategori(models.Model):
    nama = models.CharField(
        max_length=100,
        unique=True
    )

    def __str__(self):
        return self.nama
    

# =========================
# MASTER SIKLUS
# =========================
class Siklus(models.Model):

    nama = models.CharField(
        max_length=100,
        unique=True
    )

    keterangan = models.TextField(
        blank=True,
        null=True
    )

    def __str__(self):
        return self.nama


# =========================
# PESANAN
# =========================
from django.utils import timezone

class Pesanan(models.Model):

    operator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="pesanan"
    )

    # waktu pesanan dibuat (UNTUK DASHBOARD / GRAFIK)
    created_at = models.DateTimeField(auto_now_add=True)

    # tanggal pemesanan (jadwal menu dikirim)
    tanggal_pemesanan = models.DateField()

    siklus_menu = models.ForeignKey(
        'Siklus',
        on_delete=models.CASCADE,
        related_name='pesanan'
    )

    jumlah_pasien = models.IntegerField(default=0)
    jumlah_karyawan = models.IntegerField(default=0)

    def __str__(self):
        return f"Pesanan #{self.id} - {self.tanggal_pemesanan}"


# =========================
# ITEM PESANAN
# =========================
class ItemPesanan(models.Model):
    pesanan = models.ForeignKey(
        Pesanan,
        on_delete=models.CASCADE,
        related_name="items"
    )
    bahan = models.ForeignKey(Bahan, on_delete=models.CASCADE)
    qty = models.FloatField()
    keterangan = models.TextField(blank=True, null=True)  # wajib ada

    def __str__(self):
        return f"{self.bahan.nama} - {self.qty} {self.bahan.satuan}"


# =========================
# TEMPLATE / FAVORIT PESANAN
# =========================
class TemplatePesanan(models.Model):
    nama = models.CharField(
        max_length=100
    )
    operator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="template_pesanan"
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.nama


class TemplateItem(models.Model):
    template = models.ForeignKey(
        TemplatePesanan,
        on_delete=models.CASCADE,
        related_name="items"
    )
    bahan = models.ForeignKey(
        Bahan,
        on_delete=models.CASCADE
    )
    qty = models.FloatField()

    def __str__(self):
        return f"{self.bahan.nama} - {self.qty}"
