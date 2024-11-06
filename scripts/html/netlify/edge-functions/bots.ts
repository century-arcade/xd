export default async (request) => {
  const userAgent = request.headers.get('user-agent') || '';

if (!userAgent.length || userAgent.startsWith("Python-urllib") {
    return new Response('Access Denied', {
      status: 403,
      headers: {
        'Content-Type': 'text/plain'
      }
    });
  }

  return;
};

export const config = {path: '/*'}
