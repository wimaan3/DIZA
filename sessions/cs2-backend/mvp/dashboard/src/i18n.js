import EXTRA from './i18n-extra.js';
// Dashboard text in the operator's language. The English sentence is the key, so code stays readable and a missing
// translation falls back to English. {name} placeholders are filled from vars. Caller quotes and transcripts are never
// translated: operators need the exact words. zh and es are machine-quality drafts: have a native speaker review them.
export const LANGUAGES={en:'English',zh:'中文',es:'Español'};
let current='en';
export const setLanguage=l=>{current=LANGUAGES[l]?l:'en';document.documentElement.lang=current==='zh'?'zh-CN':current};
export const language=()=>current;
export const locale=()=>({en:'en-US',zh:'zh-CN',es:'es-ES'}[current]);
// "119 fire / 120 ambulance / 110 police" in the operator's language, from the region's number table.
export const emergencyText=r=>r?Object.entries(r.numbers).filter(([k])=>k!=='also').map(([k,v])=>k==='all'?v:`${v} ${t(k)}`).slice(0,3).join(' / '):'911';
export function t(key,vars={}){
 const s=EXTRA[current]?.[key]||DICT[current]?.[key]||key;
 return s.replace(/\{(\w+)\}/g,(_,k)=>vars[k]??`{${k}}`);
}
const DICT={
 zh:{
  'Done':'已完成','Finished by the person assigned':'已由负责人完成','Nothing finished yet.':'暂无已完成事项。',
  'All':'全部','Filter by category':'按类别筛选',
  'Senior care':'长者照护','Mark done':'标记完成','Answer once; every later caller with this question gets it':'回答一次，之后问同样问题的来电者都会听到','Source (link or office)':'来源（链接或部门）','Approve':'批准',
  'New report':'新报告','Show':'查看','Dismiss':'关闭',
  'All reports':'查看全部事件','Care locations':'养老设施','Jump to':'跳转至','Deployment area':'服务区域','Facility website':'机构官网',
  'Approximate address position. Verify facility availability.':'地址位置为近似值，请向机构核实服务情况。',
  '3D buildings appear when zoomed in. Heights may be estimated.':'放大后可见 3D 建筑，部分高度为估计值。',
  'Map loading slowly. Try Offline map.':'地图加载较慢，可切换离线地图。','Map data unavailable. Try Offline map.':'地图数据暂不可用，可切换离线地图。',
  '3D graphics unavailable. Event cards remain available below.':'3D 图形不可用，仍可使用下方事件卡片。',
  'off duty':'下班','Covers':'负责区域','{n} km around home':'住处周边 {n} 公里','Hours':'值班时间','Backup':'后备人员','evac logistics':'疏散后勤','mental health':'心理支持',listener:'倾听',logistics:'后勤',security:'安保',safety:'安全',facilities:'设施',volunteer:'志愿者',general:'通用',
  police:'报警',ambulance:'急救','LIVE LINE · DRILL':'在线 · 演练','LIVE LINE':'在线','SIMULATION':'模拟','Live · connected to Retell':'在线 · 已连接 Retell',
  'Backend connected · no phone line':'后端已连接 · 无电话线路','Not connected':'未连接','Simulation (no Retell key)':'模拟（无 Retell 密钥）','New demo report':'新建演示报告',
  'Simulation mode.':'模拟模式。','No phone line is connected (RETELL_API_KEY not set). Reports here are entered by hand.':'未连接电话线路（未设置 RETELL_API_KEY）。这里的报告为手动录入。',
  // shell
  'Building':'楼宇','911 operations':'应急调度','Supporter inbox':'支援人员收件箱','Workspace':'工作区','Night operations':'夜间值班',
  'Every handoff matters.':'每一次交接都很重要。','A notification is not an accepted responsibility.':'通知不等于已接手负责。',
  'A clear picture. A human response.':'看清全局，由人来响应。','Understand what is happening. See who still needs help.':'了解现场情况，看清谁还需要帮助。',
  'NIGHT SHIFT / EMERGENCY LINE':'夜班 / 应急热线','Live.':'直播中。','Calls to {line} appear here as they happen.':'拨打 {line} 的来电会实时显示在这里。',
  'Drill mode: calls are practice and emergency services are never contacted by this system.':'演练模式：通话仅为练习，本系统绝不会联系紧急服务。',
  'This system never dispatches emergency services.':'本系统从不调派紧急服务。','the DIZA line':'DIZA 热线',
  'Reset drill data':'重置演练数据','Reset demo data':'重置演示数据','Region':'地区','Emergency':'紧急电话','Language':'语言',
  'Line activity':'热线动态','Calls':'通话','Follow-ups':'后续事项','Unanswered questions':'未解答问题','Alerts':'警报','Team on call':'值班团队',
  'On call':'通话中','Ended':'已结束','Inbound':'呼入','Outbound':'呼出','No calls yet. Every call to the line is logged here with its summary.':'暂无通话。每通来电都会连同摘要记录在这里。',
  'Mark available':'标记为空闲','available':'空闲','busy':'忙碌','reserved':'已预留',
  // severity and handoff
  'Life threat':'危及生命','Urgent':'紧急','Needs review':'待审核','Information':'信息咨询','Not urgent':'非紧急',
  'Unassigned':'未分配','Awaiting acceptance':'等待接受','Accepted':'已接受','Completed by responder':'响应人员已完成','Needs supervisor':'需主管处理',
  // queue
  'Operator queue unavailable':'调度队列不可用','Loading the operator queue…':'正在加载调度队列…',
  'P0–P1 · P0 pinned, then score, then wait':'P0–P1 · P0 置顶，再按分数和等待时间排序','P2–P3 · review, info, follow-ups':'P2–P3 · 审核、咨询、后续事项',
  'P0 pinned on top, then score, then wait':'P0 置顶，再按分数和等待时间排序','No urgent reports right now.':'目前没有紧急报告。','Nothing waiting.':'没有待处理事项。',
  'I am':'我是','move':'移动','take call':'接听','merge':'合并','priority':'优先级','callback':'回拨','reviewed':'已审核',
  'Load demo: falls & freeway crash':'加载演示：老人跌倒与高速车祸','Simulate surge':'模拟激增','Wall view ↗':'大屏视图 ↗','No reports yet.':'暂无报告。',
  'Calls to the line appear here within seconds. In drill mode, load the demo (elderly falls and a freeway crash) to see a busy night.':'来电会在几秒内出现在这里。演练模式下可加载演示（老人跌倒与高速车祸），查看繁忙夜晚的情形。',
  'taken':'已接手','handled':'已处理','Location not given yet':'尚未提供位置','waiting {t}':'已等待 {t}','raised from {s}':'由 {s} 上调',
  '{n} callers':'{n} 位来电者','no pin':'无定位','on call':'通话中',
  // incident card
  'Incident card':'事件卡','UNVERIFIED REPORT':'未核实报告','Caller ••{x}':'来电者 ••{x}','Second reader':'复核规则',
  'Possible missed danger: caller said “{w}”':'可能遗漏的危险：来电者说了“{w}”','(may be “{m}” misheard)':'（可能是“{m}”被误听）',
  'AI filed it as {s} {c}; “{k}” implies {i}':'AI 记录为 {s} {c}；“{k}” 意味着 {i}','AI filed it as {c}; the caller mentioned {k}':'AI 记录为 {c}；来电者提到了 {k}',
  'Reviewed by {who}: {note}':'由 {who} 审核：{note}','Priority raised until a person reviews it.':'在人工审核前优先级保持上调。',
  'Take call':'接听','Taken by {who}':'由 {who} 接手','Callback':'回拨','Reviewed':'已审核','Merge':'合并',
  'Link this report to the incident at':'将此报告关联到以下事件','Choose an incident…':'选择事件…','Unlink from its incident':'取消关联',
  'Both reports stay listed; only the grouping changes.':'两份报告都会保留，只改变分组。','Responsibility':'责任','{n}s to accept':'剩余 {n} 秒接受',
  'Flag for supervisor review':'提交主管审核','Offer to eligible responder':'分派给合适的响应人员',
  'Immediate danger reported. Contact emergency services directly ({num}). DIZA does not dispatch or call them.':'报告有紧急危险。请直接联系紧急服务（{num}）。DIZA 不会调派或呼叫他们。',
  'Information request recorded. No follow-up task was created.':'已记录信息咨询，未创建后续任务。','Priority score {n}':'优先级分数 {n}',
  'Rule-based ranking · not a validated emergency triage system.':'基于规则的排序 · 并非经验证的紧急分诊系统。',
  'COMPLETENESS':'信息完整度','Not collected yet':'尚未收集','Exact location shared by caller':'来电者共享的精确位置','Open in Google Maps':'在 Google 地图中打开',
  'Agency for this location:':'该位置的主管机构：',"CALLER'S WORDS":'来电者原话','No caller quote recorded.':'没有记录来电者原话。',
  'LIVE TRANSCRIPT':'实时转写','TRANSCRIPT':'通话转写','Agent':'AI 助手','Caller':'来电者',
  'CORROBORATION · shown, never used to hide a card':'佐证 · 仅供参考，绝不用于隐藏事件卡','independent callers':'位独立来电者','{n} reports in this incident':'此事件共 {n} 份报告',
  'on scene':'在现场','{n} third party':'{n} 位第三方','with GPS':'有 GPS','{n} stated address only':'{n} 份仅有口述地址','callback answered':'回拨已接通',
  'an outbound call reached them':'回拨电话已联系上','Yes':'是','No':'否','TIMELINE':'时间线','No actions yet.':'暂无操作。',
  'Lower {a} → {b}: why? (logged on the card)':'将 {a} 降为 {b}：原因？（会记录在事件卡上）','Mark reviewed: what did you check? (logged on the card)':'标记已审核：你核实了什么？（会记录在事件卡上）',
  'Location verified':'位置已核实','Callback number':'回拨号码','On scene or third party':'在现场或第三方','What is happening':'发生了什么','People involved':'涉及人数','Hazards':'危险因素','Access needs':'行动不便需求',
  '{s} base':'{s} 基础分','{n} people':'{n} 人','{n} independent callers':'{n} 位独立来电者','(possible)':'（可能）',
  fall:'跌倒',trapped:'被困',breathing:'呼吸困难',unconscious:'失去意识',weapon:'武器',bleeding:'出血',injured:'受伤',fire:'火灾',smoke:'烟雾',flood:'洪水',
  medical:'医疗',power:'停电',infrastructure:'基础设施','safety crime':'治安',other:'其他',info:'咨询',gas:'燃气','welfare check':'安危探访',
  // load strip
  'Calls handled with no operator':'无需调度员处理的来电','of {n}':'共 {n}','{n} warm transfers to a person':'{n} 次转接给真人',
  'Callers answered at once (peak)':'同时接听的来电（峰值）','no hold queue while the AI takes the call':'AI 接听期间无需排队等候',
  'Duplicate reports folded':'合并的重复报告','{a} reports → {b} incidents':'{a} 份报告 → {b} 个事件',
  'Operator time saved (estimate)':'节省的调度员时间（估算）','min':'分钟','{n} answers pre-collected × {s} s each':'预先收集 {n} 项信息 × 每项 {s} 秒',
  'Call to ranked card (median)':'来电到排序事件卡（中位数）','from pickup to a card in this queue':'从接听到出现在队列中',
  'Handled outside 911':'在紧急线路之外处理','info answered + follow-ups queued':'已解答咨询 + 已排队的后续事项',
  '{n} life-threat reports with nobody on them.':'{n} 份危及生命的报告无人接手。','{n} possible missed dangers to review.':'{n} 个可能遗漏的危险待审核。',
  'Reports per 5 min · last hour':'每 5 分钟报告数 · 最近一小时','−60 min':'−60 分钟','now':'现在','What callers report':'来电内容','Languages':'语言',
  'No reports in the last 24 h.':'最近 24 小时没有报告。',
  // map
  'Live map':'实时地图','Verified place':'已核实地点','Zone ({n})':'区域（{n}）','Offline outline map · US Census TIGER data':'离线轮廓地图 · 美国人口普查局 TIGER 数据',
  'Draw zone':'绘制区域','Click the map to add corners ({n}/3+)':'点击地图添加顶点（{n}/3+）','{n} corners':'{n} 个顶点','Finish':'完成','Cancel':'取消',
  'Offline map on':'离线地图已开启','Offline map':'离线地图','Zone name, e.g. Evacuation warning north of the river':'区域名称，例如：河北岸疏散警告','Save zone':'保存区域',
  'Evacuation order':'疏散令','Evacuation warning':'疏散警告','Hazard area':'危险区域','Staging / safe area':'集结 / 安全区','Operator note':'调度员备注',
  'Click the map to place this report:':'点击地图放置此报告：','{n} without a map position':'{n} 份没有地图位置','place on map':'在地图上放置','Remove zone “{n}”?':'删除区域“{n}”？',
  'linked reports':'份关联报告','GPS from caller ±{m} m':'来电者 GPS ±{m} 米','Use the bundled outline map (works without map tiles)':'使用内置轮廓地图（无需在线地图）',
 },
 es:{
  'Done':'Hecho','Finished by the person assigned':'Terminado por la persona asignada','Nothing finished yet.':'Nada terminado todavía.',
  'All':'Todos','Filter by category':'Filtrar por categoría',
  'Senior care':'Cuidado de mayores','Mark done':'Marcar hecho','Answer once; every later caller with this question gets it':'Responda una vez; cada persona que pregunte lo mismo recibirá esta respuesta','Source (link or office)':'Fuente (enlace u oficina)','Approve':'Aprobar',
  'New report':'Nuevo reporte','Show':'Ver','Dismiss':'Cerrar',
  'All reports':'Todos los informes','Care locations':'Centros para mayores','Jump to':'Ir a','Deployment area':'Área de servicio','Facility website':'Sitio del centro',
  'Approximate address position. Verify facility availability.':'Ubicación aproximada. Confirme la disponibilidad con el centro.',
  '3D buildings appear when zoomed in. Heights may be estimated.':'Amplíe para ver edificios 3D. Las alturas pueden ser estimadas.',
  'Map loading slowly. Try Offline map.':'El mapa tarda en cargar. Pruebe el mapa sin conexión.','Map data unavailable. Try Offline map.':'Datos del mapa no disponibles. Pruebe el mapa sin conexión.',
  '3D graphics unavailable. Event cards remain available below.':'Gráficos 3D no disponibles. Puede usar las tarjetas de incidentes.',
  'off duty':'fuera de turno','Covers':'Cubre','{n} km around home':'{n} km alrededor de casa','Hours':'Horario','Backup':'Respaldo','evac logistics':'logística de evacuación','mental health':'salud mental',listener:'escucha',logistics:'logística',security:'seguridad',safety:'seguridad',facilities:'instalaciones',volunteer:'voluntario',general:'general',
  police:'policía',ambulance:'ambulancia','LIVE LINE · DRILL':'LÍNEA EN VIVO · SIMULACRO','LIVE LINE':'LÍNEA EN VIVO','SIMULATION':'SIMULACIÓN','Live · connected to Retell':'En vivo · conectado a Retell',
  'Backend connected · no phone line':'Servidor conectado · sin línea telefónica','Not connected':'Sin conexión','Simulation (no Retell key)':'Simulación (sin clave de Retell)','New demo report':'Nuevo reporte de prueba',
  'Simulation mode.':'Modo simulación.','No phone line is connected (RETELL_API_KEY not set). Reports here are entered by hand.':'No hay línea telefónica conectada (RETELL_API_KEY sin configurar). Los reportes se ingresan a mano.',
  'Building':'Edificio','911 operations':'Operaciones 911','Supporter inbox':'Bandeja de apoyo','Workspace':'Espacio de trabajo','Night operations':'Operaciones nocturnas',
  'Every handoff matters.':'Cada traspaso importa.','A notification is not an accepted responsibility.':'Una notificación no es una responsabilidad aceptada.',
  'A clear picture. A human response.':'Una imagen clara. Una respuesta humana.','Understand what is happening. See who still needs help.':'Entienda lo que pasa. Vea quién aún necesita ayuda.',
  'NIGHT SHIFT / EMERGENCY LINE':'TURNO NOCTURNO / LÍNEA DE EMERGENCIA','Live.':'En vivo.','Calls to {line} appear here as they happen.':'Las llamadas a {line} aparecen aquí en tiempo real.',
  'Drill mode: calls are practice and emergency services are never contacted by this system.':'Modo simulacro: las llamadas son de práctica y este sistema nunca contacta a los servicios de emergencia.',
  'This system never dispatches emergency services.':'Este sistema nunca despacha servicios de emergencia.','the DIZA line':'la línea DIZA',
  'Reset drill data':'Borrar datos del simulacro','Reset demo data':'Borrar datos de demostración','Region':'Región','Emergency':'Emergencia','Language':'Idioma',
  'Line activity':'Actividad de la línea','Calls':'Llamadas','Follow-ups':'Seguimientos','Unanswered questions':'Preguntas sin respuesta','Alerts':'Alertas','Team on call':'Equipo de guardia',
  'On call':'En llamada','Ended':'Terminada','Inbound':'Entrante','Outbound':'Saliente','No calls yet. Every call to the line is logged here with its summary.':'Aún no hay llamadas. Cada llamada a la línea se registra aquí con su resumen.',
  'Mark available':'Marcar disponible','available':'disponible','busy':'ocupado','reserved':'reservado',
  'Life threat':'Riesgo vital','Urgent':'Urgente','Needs review':'Por revisar','Information':'Información','Not urgent':'No urgente',
  'Unassigned':'Sin asignar','Awaiting acceptance':'Esperando aceptación','Accepted':'Aceptado','Completed by responder':'Completado por el responsable','Needs supervisor':'Requiere supervisor',
  'Operator queue unavailable':'Cola del operador no disponible','Loading the operator queue…':'Cargando la cola del operador…',
  'P0–P1 · P0 pinned, then score, then wait':'P0–P1 · P0 fijado, luego puntaje, luego espera','P2–P3 · review, info, follow-ups':'P2–P3 · revisión, información, seguimientos',
  'P0 pinned on top, then score, then wait':'P0 fijado arriba, luego puntaje, luego espera','No urgent reports right now.':'No hay reportes urgentes ahora.','Nothing waiting.':'Nada en espera.',
  'I am':'Soy','move':'mover','take call':'tomar llamada','merge':'unir','priority':'prioridad','callback':'devolver llamada','reviewed':'revisado',
  'Load demo: falls & freeway crash':'Cargar demo: caídas y choque en la autopista','Simulate surge':'Simular oleada','Wall view ↗':'Vista de pared ↗','No reports yet.':'Aún no hay reportes.',
  'Calls to the line appear here within seconds. In drill mode, load the demo (elderly falls and a freeway crash) to see a busy night.':'Las llamadas aparecen aquí en segundos. En modo simulacro, cargue la demo (caídas de adultos mayores y un choque en la autopista) para ver una noche intensa.',
  'taken':'tomada','handled':'atendida','Location not given yet':'Ubicación aún no indicada','waiting {t}':'esperando {t}','raised from {s}':'subido desde {s}',
  '{n} callers':'{n} personas llamaron','no pin':'sin punto','on call':'en llamada',
  'Incident card':'Ficha del incidente','UNVERIFIED REPORT':'REPORTE NO VERIFICADO','Caller ••{x}':'Llamante ••{x}','Second reader':'Segunda lectura',
  'Possible missed danger: caller said “{w}”':'Posible peligro omitido: la persona dijo “{w}”','(may be “{m}” misheard)':'(puede ser “{m}” mal transcrito)',
  'AI filed it as {s} {c}; “{k}” implies {i}':'La IA lo registró como {s} {c}; “{k}” implica {i}','AI filed it as {c}; the caller mentioned {k}':'La IA lo registró como {c}; la persona mencionó {k}',
  'Reviewed by {who}: {note}':'Revisado por {who}: {note}','Priority raised until a person reviews it.':'Prioridad elevada hasta que una persona lo revise.',
  'Take call':'Tomar llamada','Taken by {who}':'Tomada por {who}','Callback':'Devolver llamada','Reviewed':'Revisado','Merge':'Unir',
  'Link this report to the incident at':'Vincular este reporte al incidente en','Choose an incident…':'Elija un incidente…','Unlink from its incident':'Desvincular del incidente',
  'Both reports stay listed; only the grouping changes.':'Ambos reportes siguen en la lista; solo cambia la agrupación.','Responsibility':'Responsabilidad','{n}s to accept':'{n} s para aceptar',
  'Flag for supervisor review':'Enviar a revisión del supervisor','Offer to eligible responder':'Ofrecer a un responsable disponible',
  'Immediate danger reported. Contact emergency services directly ({num}). DIZA does not dispatch or call them.':'Se reportó peligro inmediato. Contacte directamente a emergencias ({num}). DIZA no los despacha ni los llama.',
  'Information request recorded. No follow-up task was created.':'Consulta registrada. No se creó tarea de seguimiento.','Priority score {n}':'Puntaje de prioridad {n}',
  'Rule-based ranking · not a validated emergency triage system.':'Orden por reglas · no es un sistema de triaje validado.',
  'COMPLETENESS':'DATOS COMPLETOS','Not collected yet':'Aún no recopilado','Exact location shared by caller':'Ubicación exacta compartida por la persona','Open in Google Maps':'Abrir en Google Maps',
  'Agency for this location:':'Agencia para esta ubicación:',"CALLER'S WORDS":'PALABRAS DE LA PERSONA','No caller quote recorded.':'No se registró ninguna cita.',
  'LIVE TRANSCRIPT':'TRANSCRIPCIÓN EN VIVO','TRANSCRIPT':'TRANSCRIPCIÓN','Agent':'Agente','Caller':'Llamante',
  'CORROBORATION · shown, never used to hide a card':'CORROBORACIÓN · se muestra, nunca oculta una ficha','independent callers':'llamantes independientes','{n} reports in this incident':'{n} reportes en este incidente',
  'on scene':'en el lugar','{n} third party':'{n} de terceros','with GPS':'con GPS','{n} stated address only':'{n} solo con dirección dicha','callback answered':'devolución contestada',
  'an outbound call reached them':'una llamada saliente los contactó','Yes':'Sí','No':'No','TIMELINE':'CRONOLOGÍA','No actions yet.':'Aún no hay acciones.',
  'Lower {a} → {b}: why? (logged on the card)':'Bajar {a} → {b}: ¿por qué? (queda registrado)','Mark reviewed: what did you check? (logged on the card)':'Marcar revisado: ¿qué verificó? (queda registrado)',
  'Location verified':'Ubicación verificada','Callback number':'Número para devolver','On scene or third party':'En el lugar o tercero','What is happening':'Qué está pasando','People involved':'Personas involucradas','Hazards':'Peligros','Access needs':'Necesidades de acceso',
  '{s} base':'{s} base','{n} people':'{n} personas','{n} independent callers':'{n} llamantes independientes','(possible)':'(posible)',
  fall:'caída',trapped:'atrapado',breathing:'no respira',unconscious:'inconsciente',weapon:'arma',bleeding:'sangrado',injured:'herido',fire:'incendio',smoke:'humo',flood:'inundación',
  medical:'médico',power:'sin luz',infrastructure:'infraestructura','safety crime':'seguridad',other:'otro',info:'información',gas:'gas','welfare check':'verificación de bienestar',
  'Calls handled with no operator':'Llamadas sin operador','of {n}':'de {n}','{n} warm transfers to a person':'{n} transferencias a una persona',
  'Callers answered at once (peak)':'Llamadas atendidas a la vez (pico)','no hold queue while the AI takes the call':'sin espera mientras la IA atiende',
  'Duplicate reports folded':'Reportes duplicados agrupados','{a} reports → {b} incidents':'{a} reportes → {b} incidentes',
  'Operator time saved (estimate)':'Tiempo de operador ahorrado (estimado)','min':'min','{n} answers pre-collected × {s} s each':'{n} respuestas ya recopiladas × {s} s cada una',
  'Call to ranked card (median)':'De la llamada a la ficha (mediana)','from pickup to a card in this queue':'desde que contesta hasta la ficha en la cola',
  'Handled outside 911':'Atendido fuera del 911','info answered + follow-ups queued':'consultas respondidas + seguimientos en cola',
  '{n} life-threat reports with nobody on them.':'{n} reportes de riesgo vital sin nadie asignado.','{n} possible missed dangers to review.':'{n} posibles peligros omitidos por revisar.',
  'Reports per 5 min · last hour':'Reportes cada 5 min · última hora','−60 min':'−60 min','now':'ahora','What callers report':'Qué reportan','Languages':'Idiomas',
  'No reports in the last 24 h.':'Sin reportes en las últimas 24 h.',
  'Live map':'Mapa en vivo','Verified place':'Lugar verificado','Zone ({n})':'Zona ({n})','Offline outline map · US Census TIGER data':'Mapa sin conexión · datos TIGER del Censo de EE. UU.',
  'Draw zone':'Dibujar zona','Click the map to add corners ({n}/3+)':'Haga clic en el mapa para añadir vértices ({n}/3+)','{n} corners':'{n} vértices','Finish':'Terminar','Cancel':'Cancelar',
  'Offline map on':'Mapa sin conexión activo','Offline map':'Mapa sin conexión','Zone name, e.g. Evacuation warning north of the river':'Nombre de la zona, p. ej. Aviso de evacuación al norte del río','Save zone':'Guardar zona',
  'Evacuation order':'Orden de evacuación','Evacuation warning':'Aviso de evacuación','Hazard area':'Zona de peligro','Staging / safe area':'Zona segura / de reunión','Operator note':'Nota del operador',
  'Click the map to place this report:':'Haga clic en el mapa para ubicar este reporte:','{n} without a map position':'{n} sin ubicación en el mapa','place on map':'ubicar en el mapa','Remove zone “{n}”?':'¿Eliminar la zona “{n}”?',
  'linked reports':'reportes vinculados','GPS from caller ±{m} m':'GPS de la persona ±{m} m','Use the bundled outline map (works without map tiles)':'Usar el mapa integrado (funciona sin conexión)',
 },
};

// Only known system formats are translated; captured values remain verbatim.
export function systemText(value){
 const text=String(value??'');let m;
 if((m=text.match(/^Approximate \(address lookup\): (.*)$/)))return t('Approximate (address lookup): {location}',{location:m[1]});
 if((m=text.match(/^Caller ••(.*)$/)))return t('Caller ••{x}',{x:m[1]});
 if((m=text.match(/^GPS from caller ±(.*) m$/)))return t('GPS from caller ±{m} m',{m:m[1]});
 if((m=text.match(/^(\d+) people$/)))return t('{n} people',{n:m[1]});
 return t(text);
}
