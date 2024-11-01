export default async (request) => {
  const userAgent = request.headers.get('user-agent') || '';

if (!userAgent.length) {
    return new Response('Access Denied: User-Agent is required', {
      status: 403,
      headers: {
        'Content-Type': 'text/plain'
      }
    });
  }

  return;
};

export const config = {path: '/*'}
