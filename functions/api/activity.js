const allowedEvents = new Set(['calculation', 'comparison', 'share', 'checklist']);

export async function onRequestPost(context) {
  const origin = context.request.headers.get('Origin');
  const expectedOrigin = new URL(context.request.url).origin;
  if (origin && origin !== expectedOrigin) {
    return new Response(null, { status: 403 });
  }

  let payload;
  try {
    payload = await context.request.json();
  } catch {
    return new Response(null, { status: 400 });
  }

  if (!allowedEvents.has(payload?.event)) {
    return new Response(null, { status: 400 });
  }

  context.env.ACTIVITY_EVENTS.writeDataPoint({
    blobs: [payload.event],
    doubles: [],
    indexes: []
  });
  return new Response(null, { status: 204, headers: { 'Cache-Control': 'no-store' } });
}
