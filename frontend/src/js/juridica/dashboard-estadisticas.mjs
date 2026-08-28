function inicioDia(fecha) {
    return new Date(fecha.getFullYear(), fecha.getMonth(), fecha.getDate());
}

export function calcularEstadisticasRadicacion(contratos, referencia = new Date()) {
    const hoy = inicioDia(referencia);
    const inicioSemana = new Date(hoy);
    inicioSemana.setDate(hoy.getDate() - ((hoy.getDay() + 6) % 7));

    const inicioMes = new Date(hoy.getFullYear(), hoy.getMonth(), 1);
    const inicioAnio = new Date(hoy.getFullYear(), 0, 1);
    const siguienteDia = new Date(hoy);
    siguienteDia.setDate(hoy.getDate() + 1);
    const siguienteSemana = new Date(inicioSemana);
    siguienteSemana.setDate(inicioSemana.getDate() + 7);
    const siguienteMes = new Date(hoy.getFullYear(), hoy.getMonth() + 1, 1);
    const siguienteAnio = new Date(hoy.getFullYear() + 1, 0, 1);

    const radicaciones = contratos
        .map((contrato) => ({
            fecha: new Date(contrato.created_at),
            tipo: contrato.tipo_codigo === "OS" ? "OS" : "C",
        }))
        .filter((item) => !Number.isNaN(item.fecha.getTime()));

    const contar = (desde, hasta) =>
        radicaciones.filter((item) => item.fecha >= desde && item.fecha < hasta).length;
    const delAnio = radicaciones.filter(
        (item) => item.fecha >= inicioAnio && item.fecha < siguienteAnio
    );

    return {
        hoy: contar(hoy, siguienteDia),
        semana: contar(inicioSemana, siguienteSemana),
        mes: contar(inicioMes, siguienteMes),
        anio: delAnio.length,
        total: radicaciones.length,
        contratosAnio: delAnio.filter((item) => item.tipo === "C").length,
        ordenesAnio: delAnio.filter((item) => item.tipo === "OS").length,
        meses: Array.from({ length: 12 }, (_, mes) =>
            delAnio.filter((item) => item.fecha.getMonth() === mes).length
        ),
    };
}

function limitesPeriodo(tipo, referencia) {
    const fecha = inicioDia(referencia);
    let inicio;
    let fin;

    if (tipo === "semana") {
        inicio = new Date(fecha);
        inicio.setDate(fecha.getDate() - ((fecha.getDay() + 6) % 7));
        fin = new Date(inicio);
        fin.setDate(inicio.getDate() + 7);
    } else if (tipo === "anio") {
        inicio = new Date(fecha.getFullYear(), 0, 1);
        fin = new Date(fecha.getFullYear() + 1, 0, 1);
    } else {
        inicio = new Date(fecha.getFullYear(), fecha.getMonth(), 1);
        fin = new Date(fecha.getFullYear(), fecha.getMonth() + 1, 1);
    }
    return { inicio, fin };
}

function crearSerie(tipo, inicio, contratos) {
    const meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
    if (tipo === "semana") {
        const dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
        return dias.map((label, indice) => ({
            label,
            cantidad: contratos.filter((item) => {
                const diferencia = Math.floor((inicioDia(item._fecha) - inicio) / 86400000);
                return diferencia === indice;
            }).length,
        }));
    }
    if (tipo === "anio") {
        return meses.map((label, mes) => ({
            label,
            cantidad: contratos.filter((item) => item._fecha.getMonth() === mes).length,
        }));
    }
    const ultimoDia = new Date(inicio.getFullYear(), inicio.getMonth() + 1, 0).getDate();
    return Array.from({ length: Math.ceil(ultimoDia / 7) }, (_, indice) => {
        const desde = indice * 7 + 1;
        const hasta = Math.min(desde + 6, ultimoDia);
        return {
            label: `${desde}-${hasta}`,
            cantidad: contratos.filter(
                (item) => item._fecha.getDate() >= desde && item._fecha.getDate() <= hasta
            ).length,
        };
    });
}

export function calcularDashboardPeriodo(
    contratos,
    tipo = "mes",
    referencia = new Date()
) {
    const tipoValido = ["semana", "mes", "anio"].includes(tipo) ? tipo : "mes";
    const { inicio, fin } = limitesPeriodo(tipoValido, referencia);
    const filtrados = contratos
        .map((contrato) => ({ ...contrato, _fecha: new Date(contrato.created_at) }))
        .filter(
            (contrato) =>
                !Number.isNaN(contrato._fecha.getTime()) &&
                contrato._fecha >= inicio &&
                contrato._fecha < fin
        )
        .sort((a, b) => b._fecha - a._fecha);

    const contarEstado = (estado) =>
        filtrados.filter((contrato) => contrato.estado === estado).length;

    return {
        inicio,
        fin,
        contratos: filtrados,
        total: filtrados.length,
        activos: contarEstado("activo"),
        finalizados: contarEstado("finalizado"),
        enProceso: contarEstado("en_proceso"),
        contratosTipoC: filtrados.filter((contrato) => contrato.tipo_codigo !== "OS").length,
        ordenesTipoOS: filtrados.filter((contrato) => contrato.tipo_codigo === "OS").length,
        serie: crearSerie(tipoValido, inicio, filtrados),
    };
}

function escapeXml(valor) {
    return String(valor ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");
}

function celdaTexto(estilo, valor) {
    return `<Cell ss:StyleID="${estilo}"><Data ss:Type="String">${escapeXml(valor)}</Data></Cell>`;
}

function celdaNumero(estilo, valor) {
    const numero = Number(valor);
    if (Number.isNaN(numero)) return celdaTexto(estilo, valor ?? "");
    return `<Cell ss:StyleID="${estilo}"><Data ss:Type="Number">${numero}</Data></Cell>`;
}

function encabezadoCelda(valor) {
    return celdaTexto("Encabezado", valor);
}

function tituloPeriodoExportacion(inicio, fin, tipo) {
    const ultimo = new Date(fin);
    ultimo.setDate(fin.getDate() - 1);
    if (tipo === "anio") return `Año ${inicio.getFullYear()}`;
    if (tipo === "mes") {
        const texto = inicio.toLocaleDateString("es-CO", {
            month: "long",
            year: "numeric",
        });
        return `Mes de ${texto.charAt(0).toUpperCase()}${texto.slice(1)}`;
    }
    const formato = { day: "2-digit", month: "short", year: "numeric" };
    return `Semana del ${inicio.toLocaleDateString("es-CO", formato)} al ${ultimo.toLocaleDateString("es-CO", formato)}`;
}

function filaVacia(columnas = 14) {
    return `<Row>${Array.from({ length: columnas }, () => "<Cell/>").join("")}</Row>`;
}

function textoKpi(label) {
    return celdaTexto("KpiLabel", label);
}

function valorKpi(valor) {
    return `<Cell ss:StyleID="KpiValor"><Data ss:Type="Number">${Number(valor) || 0}</Data></Cell>`;
}

/** Genera un Excel profesional (SpreadsheetML) con título, KPIs y tabla formateada. */
export function generarExcelContratos(resumen, tipo = "mes") {
    const unidades = { dias: "días", meses: "meses", anios: "años" };
    const estados = {
        activo: "Activo",
        finalizado: "Finalizado",
        en_proceso: "En proceso",
    };
    const contratos = resumen.contratos || [];
    const periodo = tituloPeriodoExportacion(resumen.inicio, resumen.fin, tipo);
    const generado = new Date().toLocaleString("es-CO");
    const precios = { mas_iva: "Más IVA", aui: "AUI", no_aplica: "No aplica" };
    const encabezados = [
        "Número de contrato",
        "Fecha de radicación",
        "Usuario que radica",
        "Proveedor",
        "NIT del proveedor",
        "Objeto del contrato",
        "Valor",
        "Moneda",
        "Forma de pago",
        "Tipo de precio",
        "Duración",
        "Fecha de inicio",
        "Fecha de finalización",
        "Estado",
    ];
    const anchos = [18, 16, 18, 28, 16, 45, 16, 10, 28, 14, 14, 14, 16, 14];

    const filasDatos = contratos
        .map((contrato, indice) => {
            const estiloFila = indice % 2 === 0 ? "FilaClara" : "FilaAlterna";
            const estiloNumero =
                indice % 2 === 0 ? "FilaClaraNumero" : "FilaAlternaNumero";
            const estado = estados[contrato.estado] || contrato.estado;
            const estiloEstado =
                contrato.estado === "activo"
                    ? "EstadoActivo"
                    : contrato.estado === "finalizado"
                    ? "EstadoFinalizado"
                    : "EstadoProceso";
            const duracion = `${contrato.plazo_cantidad} ${
                unidades[contrato.plazo_unidad] || contrato.plazo_unidad || ""
            }`;
            const fechaRadicacion = contrato.created_at
                ? new Date(contrato.created_at).toLocaleDateString("es-CO")
                : "";
            return `
      <Row ss:AutoFitHeight="1">
        ${celdaTexto(estiloFila, contrato.codigo)}
        ${celdaTexto(estiloFila, fechaRadicacion)}
        ${celdaTexto(
            estiloFila,
            contrato.creado_por_username || `Usuario #${contrato.creado_por_id}`
        )}
        ${celdaTexto(estiloFila, contrato.proveedor_contratista)}
        ${celdaTexto(estiloFila, contrato.nit_proveedor)}
        ${celdaTexto(estiloFila, contrato.descripcion_servicio)}
        ${celdaNumero(estiloNumero, contrato.valor)}
        ${celdaTexto(estiloFila, contrato.moneda)}
        ${celdaTexto(estiloFila, contrato.forma_pago || "")}
        ${celdaTexto(estiloFila, precios[contrato.tipo_precio] || "Más IVA")}
        ${celdaTexto(estiloFila, duracion)}
        ${celdaTexto(estiloFila, contrato.fecha_inicio || "")}
        ${celdaTexto(estiloFila, contrato.fecha_fin || "")}
        ${celdaTexto(estiloEstado, estado)}
      </Row>`;
        })
        .join("");

    const filaInicioTabla = 8;
    const filaFinTabla = filaInicioTabla + Math.max(contratos.length, 1) - 1;

    return `<?xml version="1.0" encoding="UTF-8"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:x="urn:schemas-microsoft-com:office:excel"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:html="http://www.w3.org/TR/REC-html40">
 <DocumentProperties xmlns="urn:schemas-microsoft-com:office:office">
  <Title>Dashboard de radicaciones · JURICOM_BEEF</Title>
  <Author>JURICOM_BEEF</Author>
  <Created>${new Date().toISOString()}</Created>
 </DocumentProperties>
 <Styles>
  <Style ss:ID="Default" ss:Name="Normal">
   <Font ss:FontName="Calibri" ss:Size="11"/>
   <Alignment ss:Vertical="Center"/>
  </Style>
  <Style ss:ID="Titulo">
   <Font ss:FontName="Calibri" ss:Size="18" ss:Bold="1" ss:Color="#0F3D68"/>
   <Alignment ss:Vertical="Center"/>
  </Style>
  <Style ss:ID="Subtitulo">
   <Font ss:FontName="Calibri" ss:Size="12" ss:Bold="1" ss:Color="#334155"/>
  </Style>
  <Style ss:ID="Meta">
   <Font ss:FontName="Calibri" ss:Size="10" ss:Color="#64748B"/>
  </Style>
  <Style ss:ID="KpiLabel">
   <Font ss:FontName="Calibri" ss:Size="10" ss:Bold="1" ss:Color="#64748B"/>
   <Interior ss:Color="#F1F5F9" ss:Pattern="Solid"/>
   <Borders>
    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#CBD5E1"/>
    <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#CBD5E1"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#CBD5E1"/>
    <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#CBD5E1"/>
   </Borders>
  </Style>
  <Style ss:ID="KpiValor">
   <Font ss:FontName="Calibri" ss:Size="14" ss:Bold="1" ss:Color="#0F3D68"/>
   <Interior ss:Color="#FFFFFF" ss:Pattern="Solid"/>
   <Borders>
    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#CBD5E1"/>
    <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#CBD5E1"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#CBD5E1"/>
    <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#CBD5E1"/>
   </Borders>
   <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
  </Style>
  <Style ss:ID="Encabezado">
   <Font ss:FontName="Calibri" ss:Size="11" ss:Bold="1" ss:Color="#FFFFFF"/>
   <Interior ss:Color="#0F3D68" ss:Pattern="Solid"/>
   <Alignment ss:Horizontal="Center" ss:Vertical="Center" ss:WrapText="1"/>
   <Borders>
    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#0B2E4E"/>
    <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#0B2E4E"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#0B2E4E"/>
    <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#0B2E4E"/>
   </Borders>
  </Style>
  <Style ss:ID="FilaClara">
   <Font ss:FontName="Calibri" ss:Size="11"/>
   <Interior ss:Color="#FFFFFF" ss:Pattern="Solid"/>
   <Borders>
    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
    <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
    <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
   </Borders>
   <Alignment ss:Vertical="Center" ss:WrapText="1"/>
  </Style>
  <Style ss:ID="FilaAlterna">
   <Font ss:FontName="Calibri" ss:Size="11"/>
   <Interior ss:Color="#F8FAFC" ss:Pattern="Solid"/>
   <Borders>
    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
    <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
    <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
   </Borders>
   <Alignment ss:Vertical="Center" ss:WrapText="1"/>
  </Style>
  <Style ss:ID="FilaClaraNumero">
   <Font ss:FontName="Calibri" ss:Size="11"/>
   <NumberFormat ss:Format="#,##0.00"/>
   <Interior ss:Color="#FFFFFF" ss:Pattern="Solid"/>
   <Borders>
    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
    <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
    <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
   </Borders>
   <Alignment ss:Horizontal="Right" ss:Vertical="Center"/>
  </Style>
  <Style ss:ID="FilaAlternaNumero">
   <Font ss:FontName="Calibri" ss:Size="11"/>
   <NumberFormat ss:Format="#,##0.00"/>
   <Interior ss:Color="#F8FAFC" ss:Pattern="Solid"/>
   <Borders>
    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
    <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
    <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
   </Borders>
   <Alignment ss:Horizontal="Right" ss:Vertical="Center"/>
  </Style>
  <Style ss:ID="EstadoActivo">
   <Font ss:FontName="Calibri" ss:Size="11" ss:Bold="1" ss:Color="#166534"/>
   <Interior ss:Color="#DCFCE7" ss:Pattern="Solid"/>
   <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
   <Borders>
    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
    <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
    <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
   </Borders>
  </Style>
  <Style ss:ID="EstadoFinalizado">
   <Font ss:FontName="Calibri" ss:Size="11" ss:Bold="1" ss:Color="#374151"/>
   <Interior ss:Color="#E5E7EB" ss:Pattern="Solid"/>
   <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
   <Borders>
    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
    <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
    <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
   </Borders>
  </Style>
  <Style ss:ID="EstadoProceso">
   <Font ss:FontName="Calibri" ss:Size="11" ss:Bold="1" ss:Color="#92400E"/>
   <Interior ss:Color="#FEF3C7" ss:Pattern="Solid"/>
   <Alignment ss:Horizontal="Center" ss:Vertical="Center"/>
   <Borders>
    <Border ss:Position="Bottom" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
    <Border ss:Position="Left" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
    <Border ss:Position="Right" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
    <Border ss:Position="Top" ss:LineStyle="Continuous" ss:Weight="1" ss:Color="#E2E8F0"/>
   </Borders>
  </Style>
 </Styles>
 <Worksheet ss:Name="Radicaciones">
  <Table>
   ${anchos.map((ancho) => `<Column ss:AutoFitWidth="0" ss:Width="${ancho * 7}"/>`).join("\n   ")}
   <Row ss:Height="28">
    <Cell ss:MergeAcross="13" ss:StyleID="Titulo"><Data ss:Type="String">JURICOM_BEEF · Dashboard de radicaciones</Data></Cell>
   </Row>
   <Row>
    <Cell ss:MergeAcross="13" ss:StyleID="Subtitulo"><Data ss:Type="String">${escapeXml(periodo)}</Data></Cell>
   </Row>
   <Row>
    <Cell ss:MergeAcross="13" ss:StyleID="Meta"><Data ss:Type="String">Generado el ${escapeXml(generado)} · Contratos aprobados disponibles para Gestión Jurídica</Data></Cell>
   </Row>
   ${filaVacia()}
   <Row ss:Height="18">
    ${textoKpi("Total")}
    ${textoKpi("Activos")}
    ${textoKpi("Finalizados")}
    ${textoKpi("En proceso")}
    ${textoKpi("Contratos (C)")}
    ${textoKpi("Órdenes (OS)")}
   </Row>
   <Row ss:Height="26">
    ${valorKpi(resumen.total)}
    ${valorKpi(resumen.activos)}
    ${valorKpi(resumen.finalizados)}
    ${valorKpi(resumen.enProceso)}
    ${valorKpi(resumen.contratosTipoC)}
    ${valorKpi(resumen.ordenesTipoOS)}
   </Row>
   ${filaVacia()}
   <Row ss:Height="30">
    ${encabezados.map(encabezadoCelda).join("")}
   </Row>
   ${filasDatos || `<Row><Cell ss:MergeAcross="13" ss:StyleID="Meta"><Data ss:Type="String">Sin contratos en el período seleccionado.</Data></Cell></Row>`}
  </Table>
  <WorksheetOptions xmlns="urn:schemas-microsoft-com:office:excel">
   <FreezePanes/>
   <FrozenNoSplit/>
   <SplitHorizontal>8</SplitHorizontal>
   <TopRowBottomPane>8</TopRowBottomPane>
   <ActivePane>2</ActivePane>
  </WorksheetOptions>
  <AutoFilter x:Range="R${filaInicioTabla}C1:R${filaFinTabla}C14" xmlns="urn:schemas-microsoft-com:office:excel"/>
 </Worksheet>
</Workbook>`;
}

/** Compatibilidad: CSV plano por si se necesita. Preferir generarExcelContratos. */
export function generarCsvContratos(contratos) {
    const unidades = { dias: "días", meses: "meses", anios: "años" };
    const estados = {
        activo: "Activo",
        finalizado: "Finalizado",
        en_proceso: "En proceso",
    };
    const precios = { mas_iva: "Más IVA", aui: "AUI", no_aplica: "No aplica" };
    const encabezados = [
        "Número de contrato",
        "Fecha de radicación",
        "Usuario que radica",
        "Proveedor",
        "NIT del proveedor",
        "Objeto del contrato",
        "Valor",
        "Moneda",
        "Forma de pago",
        "Tipo de precio",
        "Duración",
        "Fecha de inicio",
        "Fecha de finalización",
        "Estado",
    ];
    const filas = contratos.map((contrato) => [
        contrato.codigo,
        contrato.created_at
            ? new Date(contrato.created_at).toLocaleDateString("es-CO")
            : "",
        contrato.creado_por_username || `Usuario #${contrato.creado_por_id}`,
        contrato.proveedor_contratista,
        contrato.nit_proveedor,
        contrato.descripcion_servicio,
        contrato.valor,
        contrato.moneda,
        contrato.forma_pago || "",
        precios[contrato.tipo_precio] || "Más IVA",
        `${contrato.plazo_cantidad} ${
            unidades[contrato.plazo_unidad] || contrato.plazo_unidad || ""
        }`,
        contrato.fecha_inicio || "",
        contrato.fecha_fin || "",
        estados[contrato.estado] || contrato.estado,
    ]);
    const celda = (valor) => `"${String(valor ?? "").replace(/"/g, '""')}"`;
    return [encabezados, ...filas]
        .map((fila) => fila.map(celda).join(";"))
        .join("\r\n");
}
