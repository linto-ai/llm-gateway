import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET() {
  return NextResponse.json({
    apiUrl: process.env.NEXT_PUBLIC_API_URL || '',
    wsUrl: process.env.NEXT_PUBLIC_WS_URL || '',
    basePath: process.env.BASE_PATH || '',
    appName: process.env.NEXT_PUBLIC_APP_NAME || 'LLM Gateway',
  });
}
