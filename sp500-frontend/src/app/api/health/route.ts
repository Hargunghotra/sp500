import { NextResponse } from 'next/server'

export async function GET() {
  return NextResponse.json({
    status: 'ok',
    host: process.env.VERCEL ? 'vercel' : 'local',
  })
}
