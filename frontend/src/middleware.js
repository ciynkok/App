import { NextResponse } from 'next/server';

export function middleware(request) {
  const { pathname } = request.nextUrl;
  
  // Get token from cookie (assuming it's stored as 'token')
  const token = request.cookies.get('token')?.value;
  
  // Check if user is trying to access auth pages while logged in
  if (pathname.startsWith('/auth') && token) {
    return NextResponse.redirect(new URL('/', request.url));
  }
  
  // Check if user is trying to access protected routes without being logged in
  const isProtectedRoute = pathname === '/' || pathname.startsWith('/dashboard');
  const isAuthPage = pathname.startsWith('/auth');
  
  if (isProtectedRoute && !token) {
    return NextResponse.redirect(new URL('/auth/login', request.url));
  }
  
  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};
