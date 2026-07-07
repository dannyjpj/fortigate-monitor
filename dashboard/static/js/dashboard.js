async function actualizarDashboard() {

    if (!document.getElementById("equipos") && !document.getElementById("tabla_ips"))
        return;

    let data;

    try {
        const r = await fetch("/api/dashboard");
        data = await r.json();
    } catch (error) {
        return;
    }

    actualizarTexto("equipos", data.equipos);
    actualizarTexto("sesiones", data.summary.sesiones);
    actualizarTexto("apps", data.summary.aplicaciones);
    actualizarTexto("politicas", data.summary.politicas);
    actualizarTexto("trafico", formatBytes(data.summary.bytes));
    actualizarTexto("servicios", data.servicios);
    actualizarTexto("destinos", data.destinos);
    actualizarTexto("redes", data.redes);

    actualizarTexto("sesiones_exec", data.summary.sesiones);
    actualizarTexto("trafico_exec", formatBytes(data.summary.bytes));
    actualizarTexto("apps_exec", data.summary.aplicaciones);

    actualizarTabla(
        "tabla_ips",
        data.dashboard.top_ips,
        ["srcip","srcmac","auth_user","srcname","network","bytes"],
        ["IP","MAC","Usuario","Nombre","Red","Bytes"]
    );

    actualizarTabla(
        "tabla_services",
        data.dashboard.top_services,
        ["service","conexiones","bytes"],
        ["Servicio","Conexiones","Trafico"]
    );

    actualizarTabla(
        "tabla_destinations",
        data.dashboard.top_destinations,
        ["dstip","conexiones","bytes"],
        ["Destino","Conexiones","Trafico"]
    );

    actualizarTabla(
        "tabla_policies",
        data.dashboard.top_policies,
        ["policyname","conexiones","bytes"],
        ["Politica","Conexiones","Trafico"]
    );

    actualizarTabla(
        "tabla_networks",
        data.dashboard.traffic_networks,
        ["network","conexiones","bytes"],
        ["Red","Conexiones","Trafico"]
    );
}

function actualizarTexto(id, valor){

    const el = document.getElementById(id);

    if (el)
        el.innerText = valor;

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

function actualizarTabla(id, datos, columnas, etiquetas){

    const tbody = document.getElementById(id);

    if (!tbody)
        return;

    tbody.innerHTML = "";

    datos.forEach(fila => {

        const tr = document.createElement("tr");

        columnas.forEach((col, index) => {

            const td = document.createElement("td");
            td.dataset.label = etiquetas[index] || col;

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

if (document.getElementById("equipos") || document.getElementById("tabla_ips")) {
    actualizarDashboard();
    setInterval(actualizarDashboard, 5000);
}

document.addEventListener("DOMContentLoaded", () => {

    const toggle = document.querySelector(".menu-toggle");
    const nav = document.getElementById("primary-nav");

    if (!toggle || !nav)
        return;

    toggle.addEventListener("click", () => {

        const open = nav.classList.toggle("is-open");
        toggle.setAttribute("aria-expanded", open ? "true" : "false");

    });

});
