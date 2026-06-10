--[HEADCOUNT PER DEPARTMENT]
select
	d.dept_name,
	count(e.employee_id) as total_employee
from employees e
join departments d on d.dept_id = e.dept_id
where e.status = 'Active'
group by d.dept_name
order by total_employee desc;
--Insight: Headcount is concentrated in People & Culture and Customer Success, which together hold ~20.51% of active staff,
--while Operations is leanest. This shapes where attrition and cost have the biggest absolute impact.

--[AVERAGE SALARY PER SALARY GROUP]
select
	e.job_level,
	round(avg(e.monthly_salary_idr)) as average_salary
from employees e
where e.status = 'Active'
group by e.job_level
order by average_salary desc;
--Insight: Average salary rises consistently across all seven levels, from ~8.1M (Intern) to ~73.4M (Head) — about a 9x spread from entry to top.
--The steepest single step is Intern to Junior (~2x), reflecting the jump from trainee to a full role;
--increments then settle into a steady ~25-45% rise per level up the ladder.

--[EMPLOYEE DISTRIBUTION PER CITY & EMPLOYMENT TYPE]
select
	e.city,
	e.employment_type,
	count(e.employee_id) as total_employee
from employees e
where e.status = 'Active'
group by e.city, e.employment_type
order by e.city, e.employment_type;
--Insight: The workforce is evenly distributed across all six locations (each ~600-665 active staff) with no single hub
--Remote is a full peer to the physical offices (~636), confirming the company genuinely operates distributed, not office-first.
--Permanent staff dominate everywhere (~77%), with Contract (~14%) and Probation (~9%) split consistently across cities
--no location is disproportionately staffed by temporary workers.

--[EMPLOYEE DISTRIBUTION PER CITY & EMPLOYMENT TYPE 2]
--to get a better view
select
	e.employment_type,
	e.city,
	count(e.employee_id) as total_employee
from employees e
where e.status = 'Active'
group by e.employment_type, e.city
order by e.employment_type, total_employee desc;
--Reordered by employment_type then headcount desc, to see if any city concentrates a particular work type.
--Insight: No meaningful concentration, within each employment type, cities differ only slightly
--(e.g. Permanent ranges 456-513 across cities). Temporary staff aren't clustered in any single location;
--the even distribution seen by-city holds when viewed by-type too.