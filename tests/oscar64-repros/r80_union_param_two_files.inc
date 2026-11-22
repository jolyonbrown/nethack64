/* r80's second file: the same union and prototype, as a second file including the header */
union u_s { int a; char b; };
int f(union u_s *p);

int f(union u_s *p)
{
	return p->a;
}
