document.addEventListener("click", function (e) {
    if (e.target.id === "add-row") {
        let table = document.getElementById("bahan-table");
        let row = table.rows[0].cloneNode(true);
        row.querySelectorAll("input").forEach(input => input.value = "");
        table.appendChild(row);
    }

    if (e.target.classList.contains("remove-row")) {
        let rows = document.querySelectorAll("#bahan-table tr");
        if (rows.length > 1) {
            e.target.closest("tr").remove();
        }
    }
});


function hitungTotal() {
    let pasien = parseInt(document.getElementById("pasien")?.value || 0);
    let karyawan = parseInt(document.getElementById("karyawan")?.value || 0);
    document.getElementById("total_orang").value = pasien + karyawan;
}

document.addEventListener("input", function (e) {
    if (e.target.id === "pasien" || e.target.id === "karyawan") {
        hitungTotal();
    }
});

document.querySelectorAll(".preset").forEach(btn => {
    btn.addEventListener("click", () => {
        document.getElementById("pasien").value = btn.dataset.value;
        hitungTotal();
    });
});