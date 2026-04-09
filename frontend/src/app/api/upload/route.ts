import { writeFile, mkdir } from 'fs/promises';
import { join } from 'path';
import { randomUUID } from 'crypto';
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    const image = formData.get('image') as File | null;
    
    if (!image) {
      return NextResponse.json(
        { error: 'Ingen bild skickades' },
        { status: 400 }
      );
    }
    
    // Kontrollera filtyp
    if (!image.type.startsWith('image/')) {
      return NextResponse.json(
        { error: 'Endast bildfiler är tillåtna' },
        { status: 400 }
      );
    }
    
    // Kontrollera filstorlek (5MB)
    if (image.size > 5 * 1024 * 1024) {
      return NextResponse.json(
        { error: 'Bilden är för stor. Max 5MB.' },
        { status: 400 }
      );
    }
    
    const bytes = await image.arrayBuffer();
    const buffer = Buffer.from(bytes);
    
    // Skapa unikt filnamn
    const ext = image.name.split('.').pop() || 'jpg';
    const filename = `${randomUUID()}.${ext}`;
    
    // Skapa uploads-mappen om den inte finns
    const uploadDir = join(process.cwd(), 'public', 'uploads');
    await mkdir(uploadDir, { recursive: true });
    
    // Spara filen
    const filepath = join(uploadDir, filename);
    await writeFile(filepath, buffer);
    
    // Returnera URL till bilden
    const url = `/uploads/${filename}`;
    return NextResponse.json({ url });
    
  } catch (error) {
    console.error('Upload error:', error);
    return NextResponse.json(
      { error: 'Kunde inte ladda upp bilden' },
      { status: 500 }
    );
  }
}

// Begränsa storleken på request body
export const config = {
  api: {
    bodyParser: false, // Behövs för att hantera FormData
  },
};