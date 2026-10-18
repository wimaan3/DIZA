"""Bounded demo dialogue: hotel-approved answers and explicit request readbacks."""

import re
import unicodedata

CATEGORIES = {
    "air_conditioning": ("Air conditioning", "maintenance"),
    "water_leak": ("Water leak", "maintenance"),
    "lighting": ("Lighting issue", "maintenance"),
    "housekeeping": ("Towels / housekeeping", "housekeeping"),
    "noise": ("Noise concern", "front_desk"),
    "lockout": ("Room access", "front_desk"),
    "front_desk": ("Front desk assistance", "front_desk"),
    "safety": ("Safety concern", "front_desk"),
}


def normalized(text):
    text = "".join(
        c for c in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(c)
    )
    return " ".join(re.findall(r"[a-z0-9]+", text))


def greeting(room, language):
    if language == "es":
        return (
            f"Hola, estás hablando con el asistente de Harbor House para la habitación {room}. "
            "Puedo ayudarte con preguntas del hotel o registrar una solicitud. ¿Qué necesitas?"
        )
    return (
        f"Welcome to Harbor House, room {room}. I’m your hotel service assistant. "
        "I can answer hotel questions or help you request a service. What can I help with?"
    )


def respond(text, room, language):
    value = normalized(text)
    spanish = language == "es"
    if value in {"hi", "hello", "hey", "hola", "buenos dias", "buenas tardes"}:
        return {"kind": "greeting", "text": greeting(room, language)}
    if value in {"thanks", "thank you", "gracias", "muchas gracias"}:
        return {
            "kind": "greeting",
            "text": "Con gusto. ¿Necesitas algo más?"
            if spanish
            else "You’re welcome. Is there anything else I can help with?",
        }
    # Conservative attention flag only; never claims dispatch or makes real calls.
    danger = re.search(
        r"\b(fire|smoke|gas leak|gas smell|smell gas|unconscious|can t breathe|cannot breathe|"
        r"incendio|humo|fuga de gas|olor a gas|huele a gas|inconsciente|no puedo respirar)\b",
        value.replace("fire tv", "television"),
    )
    if danger:
        return {
            "kind": "safety",
            "category": "safety",
            "urgency": "emergency",
            "text": (
                "Si hay peligro inmediato, llama al 911. Esta demostración no puede llamar "
                "ni enviar ayuda. He registrado una alerta para revisión de recepción."
                if spanish
                else "For immediate danger, call 911. This demo cannot place calls or send help. "
                "I’ve recorded a safety alert for front desk review."
            ),
        }
    faqs = [
        (
            r"\b(wifi|wi fi|internet|password|contrasena)\b",
            "In this scenario, choose HarborHouse-Guest and open the welcome page. "
            "Select Guest access and enter your room number. No password is needed. "
            "If that does not work, tell me and I can ask the front desk to help.",
            "En este escenario, elige HarborHouse-Guest y abre la página de bienvenida. "
            "Selecciona Acceso de huéspedes e introduce tu número de habitación. "
            "No hace falta contraseña. Si no funciona, puedo pedir ayuda a recepción.",
        ),
        (
            r"\b(check out|checkout|salida)\b",
            "Checkout is at 11:00 AM in this demo hotel. "
            "For a late checkout request, I can ask the front desk to review availability.",
            "La salida es a las 11:00 en este hotel de demostración. "
            "Para salir más tarde, puedo pedir a recepción que revise la disponibilidad.",
        ),
        (
            r"\b(breakfast|desayuno)\b",
            "Breakfast is served from 7:00 to 10:00 AM in the ground-floor dining room "
            "in this demo hotel.",
            "El desayuno se sirve de 7:00 a 10:00 en el comedor de la planta baja "
            "de este hotel de demostración.",
        ),
    ]
    human_request = re.search(
        r"\b(person|human|staff|someone|still|didn t work|doesn t work|"
        r"persona|recepcion|todavia|no funciona)\b",
        value,
    )
    for pattern, english, translated in faqs:
        if re.search(pattern, value) and not human_request:
            return {"kind": "answer", "text": translated if spanish else english}
    category = "front_desk"
    for pattern, candidate in [
        (
            r"\b(ac|air conditioning|air conditioner|aire|climatizacion|cooling)\b",
            "air_conditioning",
        ),
        (r"\b(leak|leaking|fuga|gotea|inundacion|water on the floor)\b", "water_leak"),
        (r"\b(towel|towels|toalla|toallas|cleaning|housekeeping|limpieza)\b", "housekeeping"),
        (r"\b(light|lights|bulb|lighting|luz|luces|bombilla)\b", "lighting"),
        (r"\b(noise|noisy|loud|ruido|ruidoso)\b", "noise"),
        (r"\b(lockout|locked out|key|keys|llave|tarjeta|cerradura)\b", "lockout"),
    ]:
        if re.search(pattern, value):
            category = candidate
            break
    label, department = CATEGORIES[category]
    urgency = "priority" if category in {"water_leak", "lockout"} else "routine"
    return {
        "kind": "request",
        "category": category,
        "department": department,
        "urgency": urgency,
        "summary": label,
        "quote": text,
        "text": (
            f"Puedo registrar tu solicitud para la habitación {room}. "
            "Revisa los detalles de abajo y confírmalos. "
            "El personal deberá aceptar la tarea antes de que tenga un responsable."
            if spanish
            else f"I can record that request for room {room}. "
            "Please review the details below and confirm them. "
            "A staff member will need to accept the task before it has an owner."
        ),
    }
