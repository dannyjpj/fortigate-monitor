async function actualizarDashboard() {

    const r = await fetch("/api/dashboard");
    const data = await r.json();

    document.getElementById("equipos").innerText = data.equipos;
    document.getElementById("sesiones").innerText = data.summary.sesiones;
    document.getElementById("apps").innerText = data.summary.aplicaciones;
    document.getElementById("politicas").innerText = data.summary.politicas;
    document.getElementById("trafico").innerText = formatBytes(data.summary.bytes);
    document.getElementById("servicios").innerText = data.servicios;
    document.getElementById("destinos").innerText = data.destinos;
    document.getElementById("redes").innerText = data.redes;

    actualizarTabla(
        "tabla_ips",
        data.dashboard.top_ips,
        ["srcip","srcname","network","bytes"]
    );

    actualizarTabla(
        "tabla_services",
        data.dashboard.top_services,
        ["service","conexiones","bytes"]
    );

    actualizarTabla(
        "tabla_destinations",
        data.dashboard.top_destinations,
        ["dstip","conexiones","bytes"]
    );

    actualizarTabla(
        "tabla_policies",
        data.dashboard.top_policies,
        ["policyname","conexiones","bytes"]
    );

    actualizarTabla(
        "tabla_networks",
        data.dashboard.traffic_networks,
        ["network","conexiones","bytes"]
    );
}

function formatBytes(bytes){

    if(bytes==null)
        return "0 B";

    const unidades=["B","KB","MB","GB","TB"];

    let i=0;

    while(bytes>=1024 && i<unidades.length-1){

        bytes/=1024;

        i++;

    }

    return bytes.toFixed(2)+" "+unidades[i];

}

function actualizarTabla(id, datos, columnas){

    const tbody = document.getElementById(id);

    if (!tbody)
        return;

    tbody.innerHTML = "";

    datos.forEach(fila => {

        const tr = document.createElement("tr");

        columnas.forEach(col => {

            const td = document.createElement("td");

            let valor = fila[col];

            if (col === "bytes")
                valor = formatBytes(valor);

            if (valor === null || valor === undefined || valor === "")
                valor = "-";

            td.textContent = valor;

            tr.appendChild(td);

        });

        tbody.appendChild(tr);

    });

}

actualizarDashboard();

setInterval(actualizarDashboard, 5000);
