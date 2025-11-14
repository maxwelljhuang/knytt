// Cloudflare Pages Function to proxy product API requests
export async function onRequest(context: any) {
  const { params, request } = context;
  const productId = params.id;

  const API_URL = "https://knytt-api-prod-kouzugqpra-uc.a.run.app";

  try {
    const response = await fetch(`${API_URL}/api/v1/products/${productId}`, {
      method: request.method,
      headers: {
        "Content-Type": "application/json",
      },
    });

    const data = await response.json();

    return new Response(JSON.stringify(data), {
      status: response.status,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      },
    });
  } catch (error) {
    return new Response(JSON.stringify({ error: "Failed to fetch product" }), {
      status: 500,
      headers: {
        "Content-Type": "application/json",
      },
    });
  }
}
