SELECT source, fetched_at_date, count(*) 
FROM dashboard_view 
group by `source`, `fetched_at_date` 
ORDER BY `fetched_at_date` DESC;