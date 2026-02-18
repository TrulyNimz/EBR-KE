import { NextRequest, NextResponse } from 'next/server';
import { getToken } from 'next-auth/jwt';

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - api/auth (NextAuth routes)
     * - _next/static (static files)
     * - _next/image (image optimization)
     * - favicon.ico
     * - public folder
     */
    '/((?!api/auth|_next/static|_next/image|favicon.ico|public).*)',
  ],
};

// Public routes that don't require authentication
const publicRoutes = ['/login', '/forgot-password', '/reset-password'];

export async function middleware(request: NextRequest) {
  const { pathname, hostname } = request.nextUrl;

  // Extract tenant from subdomain
  const tenant = extractTenant(hostname);

  // Check if route is public
  const isPublicRoute = publicRoutes.some((route) => pathname.startsWith(route));

  // Get session token
  const token = await getToken({
    req: request,
    secret: process.env.NEXTAUTH_SECRET,
  });

  // Redirect to login if not authenticated and trying to access protected route
  if (!isPublicRoute && !token) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('callbackUrl', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Redirect to dashboard if authenticated and trying to access login
  if (isPublicRoute && token) {
    return NextResponse.redirect(new URL('/dashboard', request.url));
  }

  // Add tenant ID to headers for API requests
  const response = NextResponse.next();
  if (tenant) {
    response.headers.set('x-tenant-id', tenant);
  }

  return response;
}

/**
 * Extract tenant from hostname.
 * Supports subdomain-based multi-tenancy: tenant.ebr-app.com
 */
function extractTenant(hostname: string): string | null {
  // Skip for localhost development
  if (hostname.includes('localhost') || hostname.includes('127.0.0.1')) {
    // Could use query param or header in development
    return null;
  }

  // Extract subdomain
  const parts = hostname.split('.');
  if (parts.length >= 3) {
    const subdomain = parts[0];
    // Skip common subdomains
    if (subdomain !== 'www' && subdomain !== 'app') {
      return subdomain;
    }
  }

  return null;
}
