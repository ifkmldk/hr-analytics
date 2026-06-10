--[SELF JOIN ORGANIZATION STRUCTURE]
select
	e.employee_id,
	e.full_name,
	e.gender,
	ed.dept_name,
	e.job_level,
	m.employee_id as manager_id,
	m.full_name as manager_name,
	m.gender as manager_gender,
	md.dept_name as manager_department,
	m.job_level as manager_level
from employees e
left join employees m on m.employee_id = e.manager_id
join departments ed on ed.dept_id = e.dept_id
left join departments md on md.dept_id = m.dept_id
where e.status = 'Active' and (m.status = 'Active' or m.employee_id is null)
order by e.full_name;

--[SELF JOIN SUBORDINATE COUNTS]
select
	m.full_name,
	md.dept_name,
	count(e.employee_id) as total_subordinates,
	rank() over (order by count(e.employee_id) desc) as rank_by_subordinates
from employees m
left join employees e on e.manager_id = m.employee_id and e.status = 'Active'
join departments md on md.dept_id = m.dept_id
where m.status = 'Active'
group by m.employee_id, m.full_name, md.dept_name
order by rank_by_subordinates;