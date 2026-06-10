--[REVIEW SCORE TREND PER PERIOD]
with period_stats as (
    select
        pr.review_period,
        avg(pr.review_score)::numeric as avg_score,
        stddev(pr.review_score)::numeric as std_score
    from performance_reviews pr
    group by pr.review_period
)
select
    review_period,
    round(avg_score, 2) as avg_review_score,
    round(std_score, 2) as score_stddev,
    round(avg_score - std_score, 2) as bottom_limit,
    round(avg_score + std_score, 2) as upper_limit
from period_stats
order by review_period;
--Insight: Review scores held steady at ~3.49 (σ~0.78) across all periods
--stable and consistent, with no upward or downward trend over two years.

--[GOAL ACHIEVEMENT PER DEPARTMENT]
with employee_achievements as (
	select
		e.employee_id,
		e.dept_id,
		coalesce((sum(g.achievement_pct * g.weight_pct) / nullif(sum(g.weight_pct), 0))::numeric, 0) as overall_achievement
	from employees e
	join goals g on g.employee_id = e.employee_id
	group by e.employee_id, e.dept_id
)
select
	d.dept_name,
	round(avg(ea.overall_achievement),2) as avg_achievement
from employee_achievements ea
join departments d on d.dept_id = ea.dept_id
group by d.dept_name
order by avg_achievement desc;
--Insight: Goal achievement is nearly identical across departments (88.1–89.7%, a 1.6-point spread).
--The uniformity itself is the finding, either performance is genuinely even, or targets are set too uniformly to differentiate teams.

--[PAY GAP BY GENDER PER LEVEL]
with pay_gaps as (
	select
	    e.job_level,
	    round(avg(e.monthly_salary_idr) filter (where e.gender = 'Male')::numeric) as avg_male,
	    round(avg(e.monthly_salary_idr) filter (where e.gender = 'Female')::numeric) as avg_female,
	    round((avg(e.monthly_salary_idr) filter (where e.gender = 'Male')- avg(e.monthly_salary_idr) filter (where e.gender = 'Female'))::numeric) as pay_gap,
	    case
	        when avg(e.monthly_salary_idr) filter (where e.gender = 'Male') > avg(e.monthly_salary_idr) filter (where e.gender = 'Female') then 'Higher for Male'
	        when avg(e.monthly_salary_idr) filter (where e.gender = 'Male') < avg(e.monthly_salary_idr) filter (where e.gender = 'Female') then 'Higher for Female'
	        else 'Equal'
	    end as gap_direction
	from employees e
	where e.gender in ('Male', 'Female')
	group by e.job_level
)
select
	pg.job_level,
	pg.avg_male,
	pg.avg_female,
	pg.pay_gap,
	case
		when gap_direction = 'Higher for Male' then round(100.0 * abs(pay_gap)/avg_male,2)
		when gap_direction = 'Higher for Female' then round(100.0 * abs(pay_gap)/pg.avg_female,2)
		else 0
	end as pay_gap_pct,
	pg.gap_direction
from pay_gaps pg
order by abs(pay_gap) desc;
--Insight: Pay gaps are small across most job levels, suggesting broadly equitable pay.
--Two levels stand out: Head (5.1% higher for male) and Intern (2.63% higher for female).
--Q: What drives the wider gap at Head level? Worth checking
--is it a small-sample effect (few Heads, so one high earner skews it), or a real seniority/negotiation pattern?