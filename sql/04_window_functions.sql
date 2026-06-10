--[TOP 3 SALARY PER DEPARTMENT]
with ranked_salary as (
	select
		e.full_name,
		e.dept_id,
		e.monthly_salary_idr,
		rank() over (partition by e.dept_id order by e.monthly_salary_idr desc) as salary_rank
	from employees e
)
select 
	d.dept_name,
	rs.salary_rank,
	rs.full_name,
	rs.monthly_salary_idr
from ranked_salary rs
join departments d on d.dept_id = rs.dept_id 
where rs.salary_rank <= 3
order by d.dept_name, rs.salary_rank;

--[PAY GAP VS DEPARTMENT-LEVEL AVERAGE]
with salary_vs_group as (
    select
        e.full_name,
        e.dept_id,
        e.job_level,
        e.monthly_salary_idr,
        round(avg(e.monthly_salary_idr) over (partition by e.dept_id, e.job_level)) as avg_dept_salary
    from employees e
)
select
    d.dept_name,
    svg.job_level,
    svg.full_name,
    svg.monthly_salary_idr,
    svg.avg_dept_salary,
    svg.monthly_salary_idr - svg.avg_dept_salary as pay_gap,
    round(100.0 * (svg.monthly_salary_idr - svg.avg_dept_salary)/svg.avg_dept_salary,2) as pay_gap_pct
from salary_vs_group svg
join departments d on d.dept_id = svg.dept_id
order by d.dept_name, svg.job_level, pay_gap desc;

--[SALARY CHANGES BY PERIOD]
with lag_salaries as (
	select 
		s.salary_id,
		s.employee_id,
		s.effective_date,
		s.monthly_salary_idr,
		s.change_reason,
		lag(s.monthly_salary_idr) over (partition by s.employee_id order by s.effective_date) as prev_salary
	from salaries s
)
select
	e.full_name,
	ls.effective_date,
	ls.monthly_salary_idr as current_salary,
	ls.prev_salary,
	ls.monthly_salary_idr - ls.prev_salary as salary_change,
	ls.change_reason
from lag_salaries ls
join employees e on e.employee_id = ls.employee_id
order by e.full_name, ls.effective_date asc;