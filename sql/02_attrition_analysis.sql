--[ATTRITION RATE]
select
	count(*) as headcount,
	count(*) filter (where e.status = 'Resigned') as resigned,
	round(100.0 * count(*) filter (where e.status = 'Resigned')/count(*),2) as attrition_rate
from employees e;
--Insight: Overall attrition is ~15%. Breaking it down by department and tenure reveals where it concentrates.

--[ATTRITION RATE PER DEPARTMENT]
select
	d.dept_name,
	count(*) as headcount,
	count(*) filter (where e.status = 'Resigned') as resigned,
	round(100.0 * count(*) filter (where e.status = 'Resigned')/count(*),2) as attrition_rate
from employees e
join departments d on d.dept_id = e.dept_id
group by d.dept_name
order by attrition_rate desc;
--Q: Why does Engineering show the highest attrition? Is it satisfaction, pay, or tenure-driven?

--[ATTRITION vs SATISFACTION]
select
	d.dept_name,
	count(*) as headcount,
	count(*) filter (where e.status = 'Resigned') as resigned,
	round(100.0 * count(*) filter (where e.status = 'Resigned')/count(*),2) as attrition_rate,
	round(avg(e.satisfaction_score)::numeric,2) as avg_satisfaction
from employees e
join departments d on d.dept_id = e.dept_id
group by d.dept_name
order by attrition_rate desc;
--Insight: Higher attrition is not matched by lower satisfaction, scores stay fairly uniform across departments (~3.3–3.7).
--Satisfaction is not the differentiator; the cause likely lies elsewhere (tenure, pay, role-fit).

--[ATTRITION vs TENURE]
with emp_tenure as (
    select
        e.*,
        -- tenure in year; use snapshot date dataset (2025-01-01)
	    extract(year from age(coalesce(nullif(e.termination_date,'')::date, date '2025-01-01'), e.hire_date::date)) as tenure_years
    from employees e
)
select
	d.dept_name,
    case
        when et.tenure_years < 1 then '0-1 yr'
        when et.tenure_years < 3 then '1-3 yr'
        when et.tenure_years < 5 then '3-5 yr'
        else '5+ yr'
    end as tenure_bucket,
    count(*) as headcount,
    count(*) filter (where et.status = 'Resigned') as resigned,
    round(100.0 * count(*) filter (where et.status = 'Resigned') / count(*), 2) as attrition_rate,
    round(avg(et.satisfaction_score)::numeric,2) as avg_satisfaction
from emp_tenure et
join departments d on d.dept_id = et.dept_id
group by d.dept_name, tenure_bucket
order by attrition_rate desc;
--Insight: Attrition is heavily concentrated in early tenure, 30–43% in year one vs under 6% after five years
--yet satisfaction stays flat (3.3–3.7) across all groups, so dissatisfaction isn't the driver.
--Q: What explains the high first-year attrition, if not satisfaction?

--[ATTRITION vs SALARY BAND]
with emp_tenure as (
    select e.*,
        extract(year from age(coalesce(nullif(e.termination_date,'')::date, date '2025-01-01'), e.hire_date::date)) as tenure_years
    from employees e
)
select
    case when et.monthly_salary_idr < d.salary_band_mid * 1000000 then 'below band' else 'at/above band' end as salary_position,
    count(*) as headcount,
    count(*) filter (where et.status = 'Resigned') as resigned,
    round(100.0 * count(*) filter (where et.status = 'Resigned') / count(*), 2) as attrition_rate
from emp_tenure et
join departments d on d.dept_id = et.dept_id
where et.tenure_years < 1
group by salary_position;
--Insight: Pay position is not the cause. Below-band and at/above-band employees leave at nearly identical rates
--in their first year (32.9% vs 31.3%), being underpaid does not explain who leaves.

--[ATTRITION vs EMPLOYMENT TYPE]
with emp_tenure as (
    select e.*,
        extract(year from age(coalesce(nullif(e.termination_date,'')::date, date '2025-01-01'), e.hire_date::date)) as tenure_years
    from employees e
)
select
    et.employment_type,
    count(*) as headcount,
    count(*) filter (where et.status = 'Resigned') as resigned,
    round(100.0 * count(*) filter (where et.status = 'Resigned') / count(*), 2) as attrition_rate
from emp_tenure et
join departments d on d.dept_id = et.dept_id
where et.tenure_years < 1
group by et.employment_type;
--Insight: Employment type explains only a little, Contract/Probation leave slightly more (~37%) than Permanent (~30%),
--but Permanent staff (the majority) still leave at 30% in year one.
--Conclusion: First-year attrition is real but its true drivers, onboarding, role-fit, manager relationship, are NOT in this dataset.
--Satisfaction and pay were both ruled out; employment type explains only a fraction.
--Recommendation: collect qualitative data (structured exit interviews, 30/60/90-day onboarding feedback),
--prioritising Engineering and Operations where first-year attrition peaks.