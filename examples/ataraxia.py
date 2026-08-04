#!/usr/bin/env python3
"""
ATARAXIA — Companion CLI untuk menemukan ketenangan jiwa.
Terinspirasi filosofi Yunani kuno (Stoisisme & Epikureanisme).

    "Ketenangan tidak datang dari dunia di sekitarmu,
     tetapi dari cara pikiranmu menyikapi dunia itu."
         — adaptasi Epictetus

Fungsi:
  * Kata-kata bijak harian (random quote)
  * Timer meditasi (fokus napas)
  * Refleksi / jurnal ketenangan
  * Kendali diri: latihan menerima apa yang tak bisa dikontrol
"""
from __future__ import annotations

import random
import sys
import time
from dataclasses import dataclass

# ---------------------------------------------------------------
# Data: kutipan & konsep
# ---------------------------------------------------------------

KUTIPAN = [
    ("Kebahagiaan dan kebebasan bermula dari satu pemahaman: "
     "ada hal yang di dalam kendali kita, dan hal lain tidak.", "Epictetus"),
    ("Kami tidak dapat memilih keadaan luar, tetapi kami selalu "
     "bisa memilih cara meresponsnya.", "Marcus Aurelius"),
    ("Bukan perkara yang mengganggumu, tetapi penilaianmu tentang "
     "perkara itu.", "Epictetus"),
    ("Hidup ini singkat. Nikmati masa kini secara bijak.", "Seneca"),
    ("Hari ini aku luput dari kecemasan; atau lebih tepat, aku "
     "menolak kecemasan itu masuk ke dalam pikiranku.", "Marcus Aurelius"),
    ("Di mana ada ketenangan, di situ ada kebijaksanaan.", "Laozi"),
]

PILAR = {
    "1": ("Ketenangan", "Sikap batin yang stabil, tak mudah goyah "
          "oleh tekanan eksternal."),
    "2": ("Kendali Diri", "Fokus pada hal yang bisa kita kendalikan; "
          "lepaskan sisanya tanpa amarah."),
    "3": ("Hidup Sederhana", "Mengurangi keinginan berlebih sebagai "
          "jalan menuju damai batin."),
    "4": ("Kejernihan", "Kebijaksanaan untuk membedakan yang perlu "
          "dari yang sia-sia."),
}


# ---------------------------------------------------------------
# Utilitas
# ---------------------------------------------------------------

def cetak_baris(ch: str = "─", n: int = 52) -> None:
    print(ch * n)


def baca_input(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return "q"


# ---------------------------------------------------------------
# Fitur-fitur
# ---------------------------------------------------------------

def tampil_kutipan() -> None:
    """Tampilkan kutipan acak."""
    kutipan, penulis = random.choice(KUTIPAN)
    cetak_baris()
    print(f'  "{kutipan}"')
    print(f"      — {penulis}")
    cetak_baris()


@dataclass
class Meditasi:
    """Timer meditasi sederhana dengan panduan napas."""

    lama_menit: int = 5

    _PANDUAN = [
        ("Tarik napas dalam-dalam selama 4 detik", 4),
        ("Tahan napas selama 4 detik", 4),
        ("Hembuskan pelan-pelan selama 6 detik", 6),
    ]

    def jalankan(self) -> None:
        total = self.lama_menit * 60
        print(f"\nBerlatih {self.lama_menit} menit. Fokus pada napasmu.\n")
        try:
            while total > 0:
                for saran, durasi in self._PANDUAN:
                    if total <= 0:
                        break
                    menit, detik = divmod(total, 60)
                    print(f"  ({menit:02d}:{detik:02d}) {saran}")
                    time.sleep(durasi)
                    total -= durasi
        except KeyboardInterrupt:
            print("\n\nSesi dihentikan. Semua baik — mulai lagi kapan pun.")
        else:
            print("\n✨ Selesai. Rileks, tersenyumlah, lanjutkan harimu. ✨")


def refleksi() -> None:
    """Jurnal refleksi singkat. Simpan ke file lokal."""
    cetak_baris()
    print("  💭 Refleksi harian — Luangkan untuk menjernihkan pikiran.")
    cetak_baris()
    jurnal = baca_input("  Apa satu hal yang bisa kamu kendalikan hari ini? > ")
    if jurnal in ("q", ""):
        return
    catatan = baca_input("  Kecemasan apa yang ingin kamu lepaskan? > ")
    teks = (
        "\n" + "─" * 52 + "\n"
        f"Waktu: {time.strftime('%Y-%m-%d %H:%M')}\n"
        f"Yang dapat kendali: {jurnal}\n"
        f"Yang dilepaskan: {catatan}\n" + "─" * 52 + "\n"
    )
    try:
        with open("jurnal_ataraxia.txt", "a", encoding="utf-8") as fh:
            fh.write(teks)
        print("\n  ✓ Tersimpan di jurnal_ataraxia.txt")
    except OSError as err:
        print(f"\n  ! Gagal menyimpan: {err}")


def latihan_kendali() -> None:
    """Latihan kognitif: pisahkan kendali vs di luar kendali."""
    ide = ["Cuaca hari ini", "Komentar orang tentangmu", "Responsmu saat marah",
           "Harga barang yang naik", "Cara kamu berbicara", "Lalu lintas",
           "Merasakan syukur", "Usahamu hari ini"]
    cetak_baris()
    print("  Latihan Kendali Diri — tebak: dalam kendalimu?")
    cetak_baris()
    benar = 0
    for kata in ide:
        jawab = baca_input(f"\n  '{kata}' → (y/n) > ")
        if jawab == "q":
            break
        dalam_kendali = kata in {"Responsmu saat marah", "Cara kamu berbicara",
                                 "Merasakan syukur", "Usahamu hari ini"}
        cocok = (jawab == "y") == dalam_kendali
        benar += cocok
        print(f"    {'✓' if cocok else '✗'} {kata} "
              f"={'dalam kendali' if dalam_kendali else 'di luar kendali'}")
    print(f"\n  Skor: {benar}/{len(ide)}  "
          f"— Ingat: fokus pada yang dalam kendalimu saja.")


# ---------------------------------------------------------------
# Menu utama
# ---------------------------------------------------------------

MENU = """
  〰〰〰 A T A R A X I A 〰〰〰
  Ketenangan jiwa yang tak terusik

  [1] Kata-kata bijak
  [2] Meditasi (timer napas)
  [3] Refleksi harian (jurnal)
  [4] Latihan kendali diri
  [5] Tentang Ataraxia
  [q] Keluar
"""


def tentang() -> None:
    cetak_baris()
    print("  Apa itu ATARAXIA?")
    cetak_baris()
    print("""
  Dari bahasa Yunani ἀταραξία (ataraxia) — 'ketenangan jiwa yang tak
  terusik'. Dipopulerkan oleh Stoisisme dan Epikureanisme sebagai
  tujuan hidup yang bahagia: kondisi di mana gejolak emosi dan
  kecemasan tidak lagi mendominasi batin.

  Pilar-pilarnya adalah:""")
    for _, (nama, desc) in PILAR.items():
        print(f"    • {nama}: {desc}")
    cetak_baris()


def main() -> None:
    print("\n✨ Selamat datang di Ataraxia — sarana tenang di tengah riuh. ✨")
    tampil_kutipan()
    while True:
        print(MENU)
        pilih = baca_input("  Pilih opsi > ").lower()
        if pilih == "q":
            print("\n  🌿 Semoga damai menyertaimu. Sampai jumpa.\n")
            break
        if pilih == "1":
            tampil_kutipan()
        elif pilih == "2":
            try:
                menit = int(baca_input("  Durasi menit (default 5) > ") or "5")
            except ValueError:
                menit = 5
            Meditasi(menit).jalankan()
        elif pilih == "3":
            refleksi()
        elif pilih == "4":
            latihan_kendali()
        elif pilih == "5":
            tentang()
        else:
            print("  ! Pilihan tidak dikenal.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n  🌿 Sampai jumpa. Tetap tenang.")
        sys.exit(0)
