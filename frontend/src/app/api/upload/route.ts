import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  const apiKey = process.env.IMGBB_API_KEY;
  if (!apiKey) {
    return NextResponse.json({ error: 'IMGBB_API_KEY saknas' }, { status: 500 });
  }

  try {
    const formData = await request.formData();
    const image = formData.get('image') as File | null;

    if (!image) {
      return NextResponse.json({ error: 'Ingen bild skickades' }, { status: 400 });
    }

    if (!image.type.startsWith('image/')) {
      return NextResponse.json({ error: 'Endast bildfiler är tillåtna' }, { status: 400 });
    }

    if (image.size > 5 * 1024 * 1024) {
      return NextResponse.json({ error: 'Bilden är för stor. Max 5MB.' }, { status: 400 });
    }

    const bytes = await image.arrayBuffer();
    const base64 = Buffer.from(bytes).toString('base64');

    const body = new URLSearchParams();
    body.append('key', apiKey);
    body.append('image', base64);

    const res = await fetch('https://api.imgbb.com/1/upload', {
      method: 'POST',
      body,
    });

    if (!res.ok) {
      const err = await res.text();
      console.error('ImgBB error:', err);
      return NextResponse.json({ error: 'Kunde inte ladda upp bilden till ImgBB' }, { status: 502 });
    }

    const data = await res.json();
    return NextResponse.json({ url: data.data.url });

  } catch (error) {
    console.error('Upload error:', error);
    return NextResponse.json({ error: 'Kunde inte ladda upp bilden' }, { status: 500 });
  }
}
