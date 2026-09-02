const allowedEvents = new Set(['calculation', 'comparison', 'share', 'checklist', 'fuel_calculation', 'mortgage_calculation', 'child_cost_calculation']);
const responseHeaders = { 'Cache-Control': 'no-store' };

function emptyResponse(status) {
  return new Response(null, { status, headers: responseHeaders });
}

export async function onRequestPost(context) {
  const origin = context.request.headers.get('Origin');
  const expectedOrigin = new URL(context.request.url).origin;
  if (origin !== expectedOrigin) {
    return emptyResponse(403);
  }

  const contentType = context.request.headers.get('Content-Type')?.split(';', 1)[0].trim().toLowerCase();
  if (contentType !== 'application/json') {
    return emptyResponse(415);
  }

  const declaredLength = Number(context.request.headers.get('Content-Length') || 0);
  if (declaredLength > 128) {
    return emptyResponse(413);
  }

  let payload;
  try {
    const body = await context.request.text();
    if (new TextEncoder().encode(body).byteLength > 128) return emptyResponse(413);
    payload = JSON.parse(body);
  } catch {
    return emptyResponse(400);
  }

  if (!allowedEvents.has(payload?.event)) {
    return emptyResponse(400);
  }

  context.env.ACTIVITY_EVENTS.writeDataPoint({
    blobs: [payload.event],
    doubles: [],
    indexes: []
  });
  return emptyResponse(204);
}
